"""
Deterministic usage signal scoring engine (Sprint 5).

Computes usage_signal_score and derived fields from evidence dicts.
Pure math — no DB access, no LLM. Matches scope doc §3 exactly.
"""
from __future__ import annotations

from datetime import date
from typing import Any

# ── Scoring weights (scope doc §3) ────────────────────────────────────

EVIDENCE_STRENGTH_WEIGHT = 0.40
RECENCY_WEIGHT = 0.25
DIVERSITY_WEIGHT = 0.15
ASSIGNEE_ACTIVITY_WEIGHT = 0.10
CPC_OVERLAP_WEIGHT = 0.10

# Tier point values per evidence piece.
TIER_POINTS = {"strong": 10, "medium": 5, "weak": 2}
MAX_EVIDENCE_STRENGTH = 40

# Confidence label thresholds.
HIGH_CONFIDENCE = 70
MEDIUM_CONFIDENCE = 40
LOW_CONFIDENCE = 20

# Self-citation threshold: flag if >30% of evidence shares an assignee.
SELF_CITE_THRESHOLD = 0.30
SELF_CITE_WEIGHT = 1 / 3


def compute_usage_signal_score(
    evidence_rows: list[dict[str, Any]],
    patent_assignees: list[str] | None = None,
    *,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Compute usage_signal_score and derived fields from evidence dicts.

    Args:
        evidence_rows: List of evidence dicts (from collector modules).
        patent_assignees: Assignees of the target patent (for self-cite detection).
        as_of_date: Reference date for recency computation (default: today).

    Returns:
        Dict with keys: score, confidence, breakdown, evidence_count,
        by_tier, by_source, has_self_citation_risk, self_citation_ratio,
        top_companies, market_categories, most_recent_date.
    """
    today = as_of_date or date.today()
    assignee_set = set(patent_assignees or [])

    if not evidence_rows:
        return _empty_result()

    # ── Evidence strength (0–40) ──────────────────────────────────
    total_strength = 0
    by_tier: dict[str, int] = {"strong": 0, "medium": 0, "weak": 0}
    by_source: dict[str, int] = {}
    assignee_counter: dict[str, int] = {}
    self_cite_count = 0
    total_cpc_overlap = 0
    most_recent_date: date | None = None
    sources_seen: set[str] = set()
    market_categories: set[str] = set()

    for row in evidence_rows:
        tier = row.get("evidence_tier", "weak")
        by_tier[tier] = by_tier.get(tier, 0) + 1

        src = row.get("source_type", "unknown")
        by_source[src] = by_source.get(src, 0) + 1
        sources_seen.add(src)

        # Per-piece point value.
        pts = TIER_POINTS.get(tier, 0)

        # Self-citation detection.
        source_assignee = row.get("source_patent_assignee") or ""
        is_self = bool(source_assignee and assignee_set and source_assignee in assignee_set)
        if is_self:
            pts *= SELF_CITE_WEIGHT
            self_cite_count += 1

        total_strength += pts
        if source_assignee:
            assignee_counter[source_assignee] = assignee_counter.get(source_assignee, 0) + 1

        # CPC overlap.
        cpc_overlap = row.get("cpc_overlap_count", 0)
        total_cpc_overlap += cpc_overlap

        # Market categories from matched CPC.
        for cpc in row.get("matched_cpc") or []:
            if cpc:
                market_categories.add(cpc[:4])  # CPC section prefix.

        # Most recent evidence date.
        filing_date = row.get("source_patent_filing_date")
        if isinstance(filing_date, date) and (most_recent_date is None or filing_date > most_recent_date):
            most_recent_date = filing_date

    evidence_strength = min(total_strength, MAX_EVIDENCE_STRENGTH)

    # ── Recency (0–25) ────────────────────────────────────────────
    recency = 0
    if most_recent_date:
        age_years = (today - most_recent_date).days / 365
        if age_years <= 2:
            recency = 25
        elif age_years <= 5:
            recency = 18
        elif age_years <= 10:
            recency = 10
        elif age_years <= 15:
            recency = 5
        # >15yr → 0

    # ── Diversity (0–15) ──────────────────────────────────────────
    diversity = 15 if len(sources_seen) >= 2 else 8

    # ── Assignee activity (0–10) ─────────────────────────────────
    distinct_assignees = len(assignee_counter)
    if distinct_assignees >= 3:
        assignee_activity = 10
    elif distinct_assignees == 2:
        assignee_activity = 6
    elif distinct_assignees == 1:
        assignee_activity = 3
    else:
        assignee_activity = 0

    # ── CPC overlap (0–10) ───────────────────────────────────────
    evidence_count = len(evidence_rows)
    avg_cpc_overlap = total_cpc_overlap / evidence_count if evidence_count else 0
    if avg_cpc_overlap >= 3:
        cpc_overlap_score = 10
    elif avg_cpc_overlap >= 2:
        cpc_overlap_score = 7
    elif avg_cpc_overlap >= 1:
        cpc_overlap_score = 4
    else:
        cpc_overlap_score = 0

    # ── Composite score ───────────────────────────────────────────
    raw = (
        evidence_strength
        + recency
        + diversity
        + assignee_activity
        + cpc_overlap_score
    )
    score = max(0, min(100, raw))

    # ── Confidence label ──────────────────────────────────────────
    if score >= HIGH_CONFIDENCE:
        confidence = "high"
    elif score >= MEDIUM_CONFIDENCE:
        confidence = "medium"
    elif score >= LOW_CONFIDENCE:
        confidence = "low"
    else:
        confidence = "low"  # "insufficient" is 12 chars, column is VARCHAR(8). Use "low".

    # ── Self-citation risk ────────────────────────────────────────
    self_cite_ratio = self_cite_count / evidence_count if evidence_count else 0.0
    has_self_citation_risk = self_cite_ratio >= SELF_CITE_THRESHOLD

    # ── Top companies (by evidence count, deduped) ────────────────
    top_companies = sorted(
        assignee_counter.items(), key=lambda x: x[1], reverse=True
    )[:5]
    top_company_names = [name for name, _ in top_companies]

    breakdown = {
        "evidence_strength": round(evidence_strength, 1),
        "recency": recency,
        "diversity": diversity,
        "assignee_activity": assignee_activity,
        "cpc_overlap": cpc_overlap_score,
        "total": score,
    }

    return {
        "score": score,
        "confidence": confidence,
        "breakdown": breakdown,
        "evidence_count": evidence_count,
        "by_tier": by_tier,
        "by_source": by_source,
        "has_self_citation_risk": has_self_citation_risk,
        "self_citation_ratio": round(self_cite_ratio, 2),
        "top_companies": top_company_names,
        "market_categories": sorted(market_categories)[:10],
        "most_recent_date": most_recent_date.isoformat() if most_recent_date else None,
    }


def _empty_result() -> dict[str, Any]:
    return {
        "score": 0,
        "confidence": "low",  # fits VARCHAR(8)
        "breakdown": {
            "evidence_strength": 0,
            "recency": 0,
            "diversity": 0,
            "assignee_activity": 0,
            "cpc_overlap": 0,
            "total": 0,
        },
        "evidence_count": 0,
        "by_tier": {"strong": 0, "medium": 0, "weak": 0},
        "by_source": {},
        "has_self_citation_risk": False,
        "self_citation_ratio": 0.0,
        "top_companies": [],
        "market_categories": [],
        "most_recent_date": None,
    }
