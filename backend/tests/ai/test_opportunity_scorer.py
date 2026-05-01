"""Tests for the rules-based opportunity scorer."""
from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.opportunity_scorer import (
    DEFAULT_WEIGHTS,
    RULES_VERSION,
    compute_score,
    extract_features,
    score_patent_opportunity,
)
from app.core.ai_models import AIArtifact
from app.core.models import PatentPublication


def _make_patent(**kwargs) -> PatentPublication:
    base = dict(
        id=uuid4(),
        doc_id=f"USPTO:OPP{uuid4().hex[:6]}",
        office="USPTO",
        publication_number="OPP001",
        title="Test patent",
        abstract="A method for testing opportunity scoring.",
        claims_text="1. A method comprising steps A, B, and C with specific signal.\n2. The method of claim 1.",
        cpc=["G06F", "H04L"],
        assignees=["Some University"],
        family_members=["A", "B", "C"],
        legal_status_confidence="estimated",
        interesting_score=72.0,
        interesting_score_version=1,
        estimated_expiry_date=date.today() + timedelta(days=400),
        tags={
            "industries": ["healthcare", "ai_ml"],
            "problem_solved": "x",
            "technology_method": ["machine_learning"],
            "materials": [],
            "novel_application_categories": ["medical_device"],
            "time_horizon": "near_term",
            "risk_flags": [],
            "opportunity_tags": ["startup_opportunity"],
            "trend_tags": [],
        },
    )
    base.update(kwargs)
    return PatentPublication(**base)


# ---------------------------------------------------------------------------
# Pure compute tests
# ---------------------------------------------------------------------------


class TestComputeScore:
    def test_returns_canonical_breakdown_shape(self) -> None:
        p = _make_patent()
        bd = compute_score(extract_features(p))
        assert 0.0 <= bd["score"] <= 100.0
        assert bd["version"] == RULES_VERSION
        assert "components" in bd
        for name in DEFAULT_WEIGHTS:
            assert name in bd["components"]
            comp = bd["components"][name]
            assert 0.0 <= comp["sub_score"] <= 1.0
            assert 0.0 <= comp["contribution"] <= 1.0

    def test_university_assignee_scores_higher_than_megacorp(self) -> None:
        uni = _make_patent(assignees=["Stanford University"])
        big = _make_patent(assignees=["IBM"])
        f_u = extract_features(uni)
        f_b = extract_features(big)
        # Same patent + same tags → only assignee_class differs.
        assert f_u.assignee_class == "university"
        assert f_b.assignee_class == "megacorp"
        s_u = compute_score(f_u)["score"]
        s_b = compute_score(f_b)["score"]
        assert s_u > s_b

    def test_expired_patent_not_zero(self) -> None:
        p = _make_patent(estimated_expiry_date=date.today() - timedelta(days=200))
        bd = compute_score(extract_features(p))
        # Expired patents should still surface (revival path).
        assert bd["score"] > 10
        assert bd["components"]["expiry_proximity"]["sub_score"] > 0


# ---------------------------------------------------------------------------
# Cache + persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_writes_artifact_and_caches(
    db_session: AsyncSession,
) -> None:
    p = _make_patent()
    db_session.add(p)
    await db_session.commit()

    bd1, art_id1 = await score_patent_opportunity(db_session, p)
    bd2, art_id2 = await score_patent_opportunity(db_session, p)

    assert bd1["score"] == bd2["score"]
    # Cache hit on second call → same artifact id, single row only.
    assert art_id1 == art_id2

    rows = (
        await db_session.execute(
            select(AIArtifact)
            .where(AIArtifact.patent_publication_id == p.id)
            .where(AIArtifact.artifact_type == "opportunity_score")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].model.startswith("rules:v")
    assert rows[0].input_tokens == 0
    assert rows[0].actual_cost_usd == 0.0


@pytest.mark.asyncio
async def test_score_recomputes_when_features_change(
    db_session: AsyncSession,
) -> None:
    p = _make_patent()
    db_session.add(p)
    await db_session.commit()

    bd1, art1 = await score_patent_opportunity(db_session, p)

    # Feature change: bump interesting_score significantly.
    p.interesting_score = 95.0
    await db_session.commit()

    bd2, art2 = await score_patent_opportunity(db_session, p)
    assert art1 != art2
    rows = (
        await db_session.execute(
            select(AIArtifact)
            .where(AIArtifact.patent_publication_id == p.id)
            .where(AIArtifact.artifact_type == "opportunity_score")
            .order_by(AIArtifact.artifact_version.asc())
        )
    ).scalars().all()
    assert len(rows) == 2
    assert rows[0].artifact_version == 1
    assert rows[1].artifact_version == 2
