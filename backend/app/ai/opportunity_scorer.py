"""
Opportunity scorer (rules-first, no LLM by default).

Phase 1 deliverable. Produces a 0-100 ``opportunity_score`` per patent
from a fixed set of features:

* expiry proximity (closer = higher)
* commercial applicability (industries + opportunity_tags)
* cross-industry applicability (number of industries + cross_industry tag)
* AI / software / material enablement (from technology_method tags)
* implementation feasibility (claims-structure heuristic)
* market relevance (industries breadth, weighted toward opportunity_tags)
* assignee type weight (university / SME upweighted)
* legal confidence
* trend momentum (TrendSnapshot z-score from weekly computation)

Every score is recorded as an ``AIArtifact(opportunity_score)`` row via
:func:`app.ai.llm_client.record_rules_artifact` so we get a per-patent,
per-weights audit trail without an LLM call. Bumping ``RULES_VERSION`` or
any ``DEFAULT_WEIGHTS`` value invalidates every prior cached artifact and
triggers recomputation on next access.

The score breakdown is the canonical content_json: callers (and the UI)
read individual component contributions from there.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import (
    RulesArtifactRequest,
    hash_rules,
    record_rules_artifact,
)
from app.ai.tagger import OPPORTUNITY_TAG_VALUES, RISK_FLAG_VALUES
from app.core.models import PatentPublication

logger = logging.getLogger(__name__)

RULES_ID = "opportunity_score_rules"
RULES_VERSION = 3  # Bumped: increased floors for missing-data scenarios

# Component weights. Sum to 1.0 by convention (rebalance if you bump
# RULES_VERSION). Each component returns a 0..1 sub-score; the final
# opportunity_score = round(100 * sum(weight_i * sub_i)).
DEFAULT_WEIGHTS: dict[str, float] = {
    "expiry_proximity": 0.18,
    "commercial_applicability": 0.14,
    "cross_industry_applicability": 0.10,
    "ai_software_enablement": 0.08,
    "implementation_feasibility": 0.10,
    "market_relevance": 0.10,
    "assignee_type_weight": 0.08,
    "legal_confidence": 0.10,
    "trend_momentum": 0.04,
    "interestingness_anchor": 0.08,
}

# Assignee classification (very rough; refined when Assignee table is
# backfilled in a later pass).
_UNIVERSITY_HINTS = (
    "university",
    "institute of technology",
    "national lab",
    "national laborator",
    "research institute",
    "academy",
    "college of",
)
_GOV_HINTS = (
    "department of",
    "ministry of",
    "naval research",
    "air force",
    "army research",
    "darpa",
)
_MEGACORP_HINTS = (
    "ibm",
    "microsoft",
    "google",
    "alphabet",
    "apple",
    "amazon",
    "meta platforms",
    "facebook",
    "samsung",
    "intel",
    "qualcomm",
    "siemens",
    "ge ",
    "general electric",
    "general motors",
    "toyota",
    "ford motor",
    "boeing",
    "lockheed",
    "raytheon",
    "pfizer",
    "merck",
    "johnson & johnson",
    "novartis",
)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------


@dataclass
class OpportunityFeatures:
    """The deterministic input fingerprint we hash for cache keys."""

    interesting_score: float | None
    interesting_score_version: int
    estimated_expiry_iso: str | None
    has_abstract: bool
    has_claims: bool
    independent_claim_count: int
    avg_claim_length: int
    industries: list[str]
    technology_method: list[str]
    materials: list[str]
    novel_application_categories: list[str]
    time_horizon: str
    risk_flags: list[str]
    opportunity_tags: list[str]
    legal_status_confidence: str
    assignee_class: str  # university | sme | megacorp | gov | unknown
    family_size: int
    cpc_section_count: int
    max_cpc_z_score: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "interesting_score": self.interesting_score,
            "interesting_score_version": self.interesting_score_version,
            "estimated_expiry_iso": self.estimated_expiry_iso,
            "has_abstract": self.has_abstract,
            "has_claims": self.has_claims,
            "independent_claim_count": self.independent_claim_count,
            "avg_claim_length": self.avg_claim_length,
            "industries": self.industries,
            "technology_method": self.technology_method,
            "materials": self.materials,
            "novel_application_categories": self.novel_application_categories,
            "time_horizon": self.time_horizon,
            "risk_flags": self.risk_flags,
            "opportunity_tags": self.opportunity_tags,
            "legal_status_confidence": self.legal_status_confidence,
            "assignee_class": self.assignee_class,
            "family_size": self.family_size,
            "cpc_section_count": self.cpc_section_count,
            "max_cpc_z_score": self.max_cpc_z_score,
        }


def _classify_assignee(assignees: list[str]) -> str:
    if not assignees:
        return "unknown"
    joined = " ".join(a.lower() for a in assignees)
    if any(h in joined for h in _UNIVERSITY_HINTS):
        return "university"
    if any(h in joined for h in _GOV_HINTS):
        return "gov"
    if any(h in joined for h in _MEGACORP_HINTS):
        return "megacorp"
    return "sme"


def _claim_features(claims_text: str | None) -> tuple[int, int]:
    """Return (independent_claim_count, avg_claim_length)."""
    if not claims_text:
        return 0, 0
    raw = claims_text.split("\n")
    claims: list[str] = []
    current: list[str] = []
    for line in raw:
        s = line.strip()
        if not s:
            continue
        if re.match(r"^\d+\.\s", s):
            if current:
                claims.append(" ".join(current))
            current = [s]
        else:
            current.append(s)
    if current:
        claims.append(" ".join(current))

    independent = [
        c for c in claims if not re.search(r"according to claim|of claim \d", c[:120].lower())
    ]
    if not claims:
        return 0, 0
    avg_len = int(sum(len(c) for c in claims) / max(1, len(claims)))
    return len(independent), avg_len


def _cpc_section_count(cpc: list[str]) -> int:
    if not cpc:
        return 0
    sections = {c[0].upper() for c in cpc if c}
    return len(sections)


def extract_features(
    patent: PatentPublication,
    cpc_z_scores: dict[str, float] | None = None,
) -> OpportunityFeatures:
    """Pure function: derive the score input fingerprint from a patent row.

    Args:
        cpc_z_scores: Optional map of CPC 4-char prefix -> z_score from
            the latest TrendSnapshot. When provided, max_cpc_z_score is set
            to the highest z-score among the patent's CPC codes.
    """
    tags = patent.tags or {}
    independent_count, avg_claim_len = _claim_features(patent.claims_text)
    cpc = patent.cpc or []

    max_z = 0.0
    if cpc_z_scores and cpc:
        for code in cpc:
            prefix = code[:4].upper() if len(code) >= 4 else code.upper()
            z = cpc_z_scores.get(prefix, 0.0)
            if z > max_z:
                max_z = z

    return OpportunityFeatures(
        interesting_score=patent.interesting_score,
        interesting_score_version=patent.interesting_score_version or 1,
        estimated_expiry_iso=(
            patent.estimated_expiry_date.isoformat()
            if isinstance(patent.estimated_expiry_date, date)
            else None
        ),
        has_abstract=bool(patent.abstract),
        has_claims=bool(patent.claims_text),
        independent_claim_count=independent_count,
        avg_claim_length=avg_claim_len,
        industries=list(tags.get("industries") or []),
        technology_method=list(tags.get("technology_method") or []),
        materials=list(tags.get("materials") or []),
        novel_application_categories=list(tags.get("novel_application_categories") or []),
        time_horizon=tags.get("time_horizon") or "unknown",
        risk_flags=list(tags.get("risk_flags") or []),
        opportunity_tags=list(tags.get("opportunity_tags") or []),
        legal_status_confidence=patent.legal_status_confidence or "estimated",
        assignee_class=_classify_assignee(patent.assignees or []),
        family_size=len(patent.family_members or []),
        cpc_section_count=_cpc_section_count(cpc),
        max_cpc_z_score=round(max_z, 4),
    )


# ---------------------------------------------------------------------------
# Component scorers (each returns 0..1)
# ---------------------------------------------------------------------------


def _score_expiry_proximity(f: OpportunityFeatures) -> float:
    """Sooner expiry → higher score; expired patents are tagged separately,
    we still give them mid-range so revival flow surfaces them."""
    if not f.estimated_expiry_iso:
        return 0.3
    try:
        d = date.fromisoformat(f.estimated_expiry_iso)
    except ValueError:
        return 0.3
    today = date.today()
    days = (d - today).days
    if days < 0:
        # Already expired: still useful (revival), but capped lower than soon-to-expire.
        years_past = abs(days) / 365.0
        return max(0.45 - 0.05 * years_past, 0.20)
    if days <= 365:
        return 1.0
    if days <= 365 * 3:
        return 0.85
    if days <= 365 * 5:
        return 0.65
    if days <= 365 * 10:
        return 0.45
    return 0.25


def _score_commercial_applicability(f: OpportunityFeatures) -> float:
    score = 0.0
    if f.industries:
        score += 0.4
    score += min(len(f.industries), 3) * 0.1
    score += min(len(set(f.opportunity_tags) & set(OPPORTUNITY_TAG_VALUES)), 3) * 0.1
    return min(score, 1.0)


def _score_cross_industry(f: OpportunityFeatures) -> float:
    score = min(len(f.industries) / 4.0, 0.6)
    if "cross_industry_transfer" in f.opportunity_tags:
        score += 0.4
    if f.cpc_section_count >= 2:
        score += 0.1
    return min(score, 1.0)


def _score_ai_software(f: OpportunityFeatures) -> float:
    keys = {
        "machine_learning",
        "computer_vision",
        "nlp",
        "signal_processing",
        "automation",
        "control_systems",
        "robotics",
    }
    overlap = set(f.technology_method) & keys
    if not overlap:
        return 0.2 if "computing" in f.industries or "ai_ml" in f.industries else 0.0
    return min(0.4 + 0.2 * len(overlap), 1.0)


def _score_implementation_feasibility(f: OpportunityFeatures) -> float:
    """High independent-claim count + moderate avg length → good signal."""
    if not f.has_claims:
        return 0.3  # was 0.2: too punishing when 96% lack claims
    icc = f.independent_claim_count
    icc_score = min(icc / 4.0, 0.5)
    # 200..1500 chars/claim is a healthy band; outside that the signal weakens.
    al = f.avg_claim_length
    if 200 <= al <= 1500:
        len_score = 0.5
    elif al == 0:
        len_score = 0.0
    else:
        len_score = 0.25
    horizon_bonus = {"now": 0.0, "near_term": 0.0, "long_term": -0.1, "unknown": -0.05}.get(
        f.time_horizon, 0.0
    )
    return max(0.0, min(icc_score + len_score + horizon_bonus, 1.0))


def _score_market_relevance(f: OpportunityFeatures) -> float:
    if not f.industries:
        return 0.3  # was 0.2: CPC sections still provide signal
    base = 0.4
    if any(
        t in {"startup_opportunity", "enterprise_automation", "manufacturing_reuse"}
        for t in f.opportunity_tags
    ):
        base += 0.3
    base += 0.1 * min(len(f.novel_application_categories), 3)
    return min(base, 1.0)


def _score_assignee_type(f: OpportunityFeatures) -> float:
    return {
        "university": 0.85,
        "sme": 0.75,
        "gov": 0.55,
        "unknown": 0.5,
        "megacorp": 0.35,
    }[f.assignee_class]


def _score_legal_confidence(f: OpportunityFeatures) -> float:
    base = 0.6 if f.legal_status_confidence == "estimated" else 1.0
    risk_set = set(f.risk_flags) & set(RISK_FLAG_VALUES)
    if "active_family_risk" in risk_set:
        base -= 0.3
    if "needs_legal_review" in risk_set:
        base -= 0.15
    if "unknown_legal_status" in risk_set:
        base -= 0.2
    return max(0.0, min(base, 1.0))


def _score_trend_momentum(f: OpportunityFeatures) -> float:
    """Map the patent's best CPC z-score from TrendSnapshot into 0..1.

    Z-score thresholds calibrated against real data where top CPC prefixes
    reach z~14 and median active prefixes sit around z~2-4.
    """
    z = f.max_cpc_z_score
    if z <= 0:
        return 0.1
    if z < 1.0:
        return 0.3
    if z < 3.0:
        return 0.5
    if z < 6.0:
        return 0.7
    if z < 10.0:
        return 0.85
    return 1.0


def _score_interestingness_anchor(f: OpportunityFeatures) -> float:
    if f.interesting_score is None:
        return 0.0
    # interesting_score is currently emitted on a 0..1 or 0..100 scale
    # depending on the legacy scorer; clamp robustly.
    s = f.interesting_score
    if s > 1.0:
        s = s / 100.0
    return max(0.0, min(s, 1.0))


COMPONENT_FUNCS = {
    "expiry_proximity": _score_expiry_proximity,
    "commercial_applicability": _score_commercial_applicability,
    "cross_industry_applicability": _score_cross_industry,
    "ai_software_enablement": _score_ai_software,
    "implementation_feasibility": _score_implementation_feasibility,
    "market_relevance": _score_market_relevance,
    "assignee_type_weight": _score_assignee_type,
    "legal_confidence": _score_legal_confidence,
    "trend_momentum": _score_trend_momentum,
    "interestingness_anchor": _score_interestingness_anchor,
}


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def compute_score(
    features: OpportunityFeatures,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Pure score computation. Returns the canonical breakdown dict.

    Shape::

        {
          "score": 0..100,
          "version": RULES_VERSION,
          "weights": {...},
          "components": {
            "<name>": {"sub_score": 0..1, "weight": 0..1, "contribution": 0..1}
          },
          "computed_at": ISO timestamp
        }
    """
    w = weights or DEFAULT_WEIGHTS
    components: dict[str, dict[str, float]] = {}
    weighted_total = 0.0
    weight_total = 0.0
    for name, fn in COMPONENT_FUNCS.items():
        sub = float(fn(features))
        ww = float(w.get(name, 0.0))
        contrib = sub * ww
        components[name] = {
            "sub_score": round(sub, 4),
            "weight": ww,
            "contribution": round(contrib, 4),
        }
        weighted_total += contrib
        weight_total += ww
    # Normalize in case the weights don't sum to exactly 1.0.
    if weight_total > 0:
        weighted_total = weighted_total / weight_total
    score = round(100.0 * max(0.0, min(weighted_total, 1.0)), 2)
    return {
        "score": score,
        "version": RULES_VERSION,
        "weights": w,
        "components": components,
        "computed_at": datetime.utcnow().isoformat(),
    }


async def _load_cpc_z_scores(session: AsyncSession) -> dict[str, float]:
    """Load the latest CPC z-scores from trend_snapshots.

    Returns a dict mapping CPC 4-char prefix -> max z_score.
    Cached per-session; cheap since there are typically < 500 CPC rows.
    """
    from app.core.ai_models import TrendSnapshot

    rows = await session.execute(
        select(TrendSnapshot.key, func.max(TrendSnapshot.z_score))
        .where(TrendSnapshot.surface == "cpc")
        .group_by(TrendSnapshot.key)
    )
    return {r[0]: float(r[1]) for r in rows}


async def score_patent_opportunity(
    session: AsyncSession,
    patent: PatentPublication,
    *,
    run_id: UUID | None = None,
    weights: dict[str, float] | None = None,
    cpc_z_scores: dict[str, float] | None = None,
) -> tuple[dict[str, Any], UUID]:
    """Compute (or fetch from cache) an opportunity_score artifact.

    Returns ``(breakdown_dict, artifact_id)``. Always returns a
    breakdown — either the cached value (if features + rules are
    unchanged) or a freshly persisted one.
    """
    if cpc_z_scores is None:
        cpc_z_scores = await _load_cpc_z_scores(session)

    features = extract_features(patent, cpc_z_scores=cpc_z_scores)
    w = weights or DEFAULT_WEIGHTS
    rules_hash = hash_rules(RULES_ID, RULES_VERSION, w)
    breakdown = compute_score(features, w)

    request = RulesArtifactRequest(
        artifact_type="opportunity_score",
        rules_id=RULES_ID,
        rules_version=RULES_VERSION,
        rules_hash=rules_hash,
        input_payload=features.as_dict(),
        content_json=breakdown,
        patent_publication_id=patent.id,
        run_id=run_id,
    )
    response = await record_rules_artifact(session, request)
    return response.content_json, response.artifact_id
