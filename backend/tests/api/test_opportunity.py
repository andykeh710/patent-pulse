"""Tests for /api/v1/opportunity list + filters + tab counts."""
from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PatentPublication


def _make(**kw) -> PatentPublication:
    base = dict(
        id=uuid4(),
        doc_id=f"USPTO:OPP{uuid4().hex[:6]}",
        office="USPTO",
        publication_number="OPP",
        title="Patent",
        abstract="abs",
        claims_text="1. A method.",
        cpc=["G06F"],
        assignees=["Acme"],
        legal_status_confidence="estimated",
        opportunity_score=60.0,
        opportunity_score_version=1,
        opportunity_breakdown={"score": 60.0, "version": 1, "components": {}},
        tags={
            "industries": ["ai_ml"],
            "problem_solved": "x",
            "technology_method": ["machine_learning"],
            "materials": [],
            "novel_application_categories": [],
            "time_horizon": "near_term",
            "risk_flags": [],
            "opportunity_tags": [],
            "trend_tags": [],
        },
    )
    base.update(kw)
    return PatentPublication(**base)


async def _seed_opportunity_patents(session: AsyncSession) -> list[PatentPublication]:
    """Seed 5 patents covering multiple tabs + sort orders."""
    today = date.today()
    patents = [
        _make(
            doc_id="USPTO:HIGH",
            publication_number="HIGH",
            title="Highest score patent",
            opportunity_score=92.0,
            interesting_score=80.0,
            estimated_expiry_date=today + timedelta(days=180),
            tags=_tags(["cross_industry_transfer", "startup_opportunity"], []),
        ),
        _make(
            doc_id="USPTO:EXPIRED",
            publication_number="EXP",
            title="Expired patent",
            opportunity_score=55.0,
            estimated_expiry_date=today - timedelta(days=400),
            tags=_tags(["public_domain_candidate", "ai_revival_candidate"], []),
        ),
        _make(
            doc_id="USPTO:LEGAL",
            publication_number="LEG",
            title="Legal review patent",
            opportunity_score=70.0,
            estimated_expiry_date=today + timedelta(days=2000),
            tags=_tags([], ["needs_legal_review"]),
        ),
        _make(
            doc_id="USPTO:SUST",
            publication_number="SUS",
            title="Sustainability patent",
            opportunity_score=65.0,
            estimated_expiry_date=today + timedelta(days=900),
            tags=_tags(["sustainability_angle"], []),
        ),
        _make(
            doc_id="USPTO:NO_SCORE",
            publication_number="NOS",
            title="Unscored patent",
            opportunity_score=None,
            opportunity_score_version=None,
            opportunity_breakdown=None,
            tags=None,
        ),
    ]
    for p in patents:
        session.add(p)
    await session.commit()
    return patents


def _tags(opp_tags: list[str], risk_flags: list[str]) -> dict:
    return {
        "industries": ["ai_ml", "healthcare"],
        "problem_solved": "x",
        "technology_method": ["machine_learning"],
        "materials": [],
        "novel_application_categories": [],
        "time_horizon": "near_term",
        "risk_flags": risk_flags,
        "opportunity_tags": opp_tags,
        "trend_tags": [],
    }


# ---------------------------------------------------------------------------
# List endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_excludes_patents_without_opportunity_score(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_opportunity_patents(db_session)
    r = await client.get("/api/v1/opportunity")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 4  # 5 seeded, 1 has no score
    doc_ids = [it["doc_id"] for it in data["items"]]
    assert "USPTO:NO_SCORE" not in doc_ids


@pytest.mark.asyncio
async def test_list_default_sort_is_opportunity_score_desc(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_opportunity_patents(db_session)
    r = await client.get("/api/v1/opportunity")
    data = r.json()
    scores = [it["opportunity_score"] for it in data["items"]]
    assert scores == sorted(scores, reverse=True)
    assert data["items"][0]["doc_id"] == "USPTO:HIGH"


@pytest.mark.asyncio
async def test_list_expired_tab_filters_to_past_expiry(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_opportunity_patents(db_session)
    r = await client.get("/api/v1/opportunity", params={"tab": "expired"})
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["doc_id"] == "USPTO:EXPIRED"


@pytest.mark.asyncio
async def test_list_legal_review_tab(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_opportunity_patents(db_session)
    r = await client.get("/api/v1/opportunity", params={"tab": "legal_review"})
    data = r.json()
    # All 4 scored patents have legal_status_confidence="estimated" + score >= 40
    # rules match. LEGAL also has the needs_legal_review tag.
    assert data["total"] == 4
    doc_ids = {it["doc_id"] for it in data["items"]}
    assert "USPTO:LEGAL" in doc_ids


@pytest.mark.asyncio
async def test_list_cross_industry_tab(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_opportunity_patents(db_session)
    r = await client.get("/api/v1/opportunity", params={"tab": "cross_industry"})
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["doc_id"] == "USPTO:HIGH"


@pytest.mark.asyncio
async def test_list_filter_by_opportunity_tag(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_opportunity_patents(db_session)
    r = await client.get(
        "/api/v1/opportunity",
        params={"opportunity_tag": "sustainability_angle"},
    )
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["doc_id"] == "USPTO:SUST"


@pytest.mark.asyncio
async def test_list_filter_by_risk_flag(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_opportunity_patents(db_session)
    r = await client.get(
        "/api/v1/opportunity", params={"risk_flag": "needs_legal_review"}
    )
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["doc_id"] == "USPTO:LEGAL"


@pytest.mark.asyncio
async def test_list_filter_by_min_score(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_opportunity_patents(db_session)
    r = await client.get("/api/v1/opportunity", params={"min_score": 70})
    data = r.json()
    doc_ids = {it["doc_id"] for it in data["items"]}
    assert doc_ids == {"USPTO:HIGH", "USPTO:LEGAL"}


@pytest.mark.asyncio
async def test_list_sort_expiring_soon(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_opportunity_patents(db_session)
    r = await client.get("/api/v1/opportunity", params={"sort": "expiring_soon"})
    data = r.json()
    # Earliest expiry first (including already-expired dates).
    ordered = [it["doc_id"] for it in data["items"]]
    assert ordered[0] == "USPTO:EXPIRED"
    assert ordered[1] == "USPTO:HIGH"


@pytest.mark.asyncio
async def test_list_pagination(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_opportunity_patents(db_session)
    r = await client.get("/api/v1/opportunity", params={"page_size": 2, "page": 1})
    data = r.json()
    assert data["total"] == 4
    assert data["page"] == 1
    assert len(data["items"]) == 2
    r2 = await client.get(
        "/api/v1/opportunity", params={"page_size": 2, "page": 2}
    )
    data2 = r2.json()
    assert len(data2["items"]) == 2
    # No overlap across pages.
    ids1 = {it["doc_id"] for it in data["items"]}
    ids2 = {it["doc_id"] for it in data2["items"]}
    assert ids1.isdisjoint(ids2)


# ---------------------------------------------------------------------------
# Tab counts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tab_counts(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_opportunity_patents(db_session)
    r = await client.get("/api/v1/opportunity/tab-counts")
    assert r.status_code == 200
    counts = r.json()
    assert counts["top"] == 4
    assert counts["expired"] == 1
    assert counts["revival"] == 1
    assert counts["cross_industry"] == 1
    assert counts["sustainability"] == 1
    # All 4 scored patents have legal_status_confidence="estimated" + score >= 40
    assert counts["legal_review"] == 4
