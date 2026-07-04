"""Trend Snapshot — rules-based artifact."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import RulesArtifactRequest, hash_rules, record_rules_artifact
from app.core.models import PatentPublication

logger = logging.getLogger(__name__)

RULES_ID = "trend_snapshot_rules"
RULES_VERSION = 1

DEFAULT_WEIGHTS: dict[str, float] = {
    "technology_momentum": 0.30,
    "cross_industry_signal": 0.25,
    "time_horizon_alignment": 0.20,
    "novel_application_breadth": 0.15,
    "industry_diversity": 0.10,
}

EMERGING_TECH = {
    "machine_learning",
    "computer_vision",
    "nlp",
    "signal_processing",
    "automation",
    "control_systems",
    "robotics",
    "quantum_computing",
    "blockchain",
    "biotechnology",
    "nanotechnology",
    "materials_science",
    "additive_manufacturing",
    "photonics",
    "sensor_networks",
}


def _momentum_score(tech: list[str], materials: list[str]) -> float:
    if not tech:
        return 0.0
    overlap = set(t.lower().replace(" ", "_") for t in tech) & EMERGING_TECH
    score = min(len(overlap) / 3.0, 0.8)
    if materials:
        score += min(len(materials) / 5.0, 0.2)
    return min(score, 1.0)


def _cross_industry(industries: list[str], novel: list[str]) -> float:
    if not industries:
        return 0.0
    score = min(len(industries) / 4.0, 0.6)
    if novel:
        score += min(len(novel) / 3.0, 0.4)
    return min(score, 1.0)


def _time_horizon(th: str) -> float:
    return {"now": 1.0, "near_term": 0.75, "long_term": 0.4, "unknown": 0.3}.get(th, 0.3)


def _novel_breadth(novel: list[str], opp_tags: list[str]) -> float:
    score = min(len(novel) / 4.0, 0.6)
    if opp_tags:
        score += min(len(opp_tags) / 5.0, 0.4)
    return min(score, 1.0)


def _industry_diversity(industries: list[str]) -> float:
    return min(len(industries) / 5.0, 1.0) if industries else 0.0


@dataclass
class TrendFeatures:
    industries: list[str]
    technology_method: list[str]
    materials: list[str]
    novel_application_categories: list[str]
    opportunity_tags: list[str]
    time_horizon: str
    family_size: int
    cpc_section_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "industries": self.industries,
            "technology_method": self.technology_method,
            "materials": self.materials,
            "novel_application_categories": self.novel_application_categories,
            "opportunity_tags": self.opportunity_tags,
            "time_horizon": self.time_horizon,
            "family_size": self.family_size,
            "cpc_section_count": self.cpc_section_count,
        }


def extract_features(patent: PatentPublication) -> TrendFeatures:
    tags = patent.tags or {}
    cpc = patent.cpc or []
    sections = {c[0].upper() for c in cpc if c}
    return TrendFeatures(
        industries=list(tags.get("industries") or []),
        technology_method=list(tags.get("technology_method") or []),
        materials=list(tags.get("materials") or []),
        novel_application_categories=list(tags.get("novel_application_categories") or []),
        opportunity_tags=list(tags.get("opportunity_tags") or []),
        time_horizon=tags.get("time_horizon") or "unknown",
        family_size=len(patent.family_members or []),
        cpc_section_count=len(sections),
    )


def compute_snapshot(
    features: TrendFeatures, weights: dict[str, float] | None = None
) -> dict[str, Any]:
    w = weights or DEFAULT_WEIGHTS
    components: dict[str, dict[str, Any]] = {}
    total = 0.0
    wt = 0.0
    funcs = {
        "technology_momentum": lambda: _momentum_score(
            features.technology_method, features.materials
        ),
        "cross_industry_signal": lambda: _cross_industry(
            features.industries, features.novel_application_categories
        ),
        "time_horizon_alignment": lambda: _time_horizon(features.time_horizon),
        "novel_application_breadth": lambda: _novel_breadth(
            features.novel_application_categories, features.opportunity_tags
        ),
        "industry_diversity": lambda: _industry_diversity(features.industries),
    }
    for name, fn in funcs.items():
        sub = float(fn())
        ww = float(w.get(name, 0.0))
        c = sub * ww
        components[name] = {"sub_score": round(sub, 4), "weight": ww, "contribution": round(c, 4)}
        total += c
        wt += ww
    if wt > 0:
        total = total / wt
    score = round(100.0 * max(0.0, min(total, 1.0)), 2)
    return {
        "trend_score": score,
        "version": RULES_VERSION,
        "weights": w,
        "components": components,
        "computed_at": datetime.utcnow().isoformat(),
    }


async def generate_trend_snapshot(
    session: AsyncSession,
    patent: PatentPublication,
    *,
    run_id: UUID | None = None,
    weights: dict[str, float] | None = None,
) -> tuple[dict[str, Any], UUID]:
    features = extract_features(patent)
    w = weights or DEFAULT_WEIGHTS
    rules_hash = hash_rules(RULES_ID, RULES_VERSION, w)
    snapshot = compute_snapshot(features, w)
    request = RulesArtifactRequest(
        artifact_type="trend_snapshot",
        rules_id=RULES_ID,
        rules_version=RULES_VERSION,
        rules_hash=rules_hash,
        input_payload=features.as_dict(),
        content_json=snapshot,
        patent_publication_id=patent.id,
        run_id=run_id,
    )
    response = await record_rules_artifact(session, request)
    return response.content_json, response.artifact_id
