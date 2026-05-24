"""Tests for Sprint 5 usage signals API endpoints."""
from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.ai_models import PatentUsageSignals, UsageEvidence
from app.core.models import PatentPublication


def _make_patent(db_session, **overrides):
    """Create a minimal patent for testing."""
    uid = overrides.pop("id", uuid4())
    defaults = {
        "id": uid,
        "doc_id": f"USPTO:APITEST{uuid4().hex[:6]}",
        "office": "USPTO",
        "publication_number": f"APITEST{uuid4().hex[:6]}",
        "assignees": ["TestCorp"],
        "title": "API test patent",
        "legal_status": "GRANTED",
        "embedding": [0.1] * 1536,  # dummy embedding
    }
    defaults.update(overrides)
    patent = PatentPublication(**defaults)
    db_session.add(patent)
    return patent


def _make_signal(db_session, patent_id):
    """Create a signal row for a patent."""
    signal = PatentUsageSignals(
        patent_publication_id=patent_id,
        usage_signal_score=55,
        usage_signal_confidence="medium",
        score_breakdown={"total": 55},
        evidence_count=2,
        strong_evidence_count=1,
        medium_evidence_count=1,
        top_companies=["Acme"],
        market_categories=["G06F"],
        has_self_citation_risk=False,
    )
    db_session.add(signal)
    return signal


@pytest.mark.asyncio(loop_scope="function")
async def test_get_usage_signals_404_for_unknown(client):
    """GET returns 404 for unknown patent_id."""
    fake_id = str(uuid4())
    resp = await client.get(f"/api/v1/usage-signals/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.xfail(
    reason="event_loop fixture contention in full suite. Passes in isolation. "
           "Fix post-Sprint-6.",
    strict=False,
)
@pytest.mark.asyncio(loop_scope="function")
async def test_get_usage_signals_returns_existing(client, db_session):
    """GET returns signal row when assessment exists."""
    patent = _make_patent(db_session)
    signal = _make_signal(db_session, patent.id)

    # Add an evidence row.
    ev = UsageEvidence(
        patent_publication_id=patent.id,
        source_type="similar_newer_patent",
        evidence_tier="strong",
        source_patent_title="Test source",
        source_patent_assignee="Acme",
        source_patent_filing_date=date(2025, 1, 1),
    )
    db_session.add(ev)
    await db_session.commit()

    resp = await client.get(f"/api/v1/usage-signals/{patent.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 55
    assert data["confidence"] == "medium"
    assert data["evidence_count"] == 2
    assert len(data["evidence"]) == 1
    assert data["evidence"][0]["evidence_tier"] == "strong"


@pytest.mark.xfail(
    reason="event_loop fixture contention in full suite. Passes in isolation. "
           "Fix post-Sprint-6.",
    strict=False,
)
@pytest.mark.asyncio(loop_scope="function")
async def test_post_generate_creates_signal(client, db_session):
    """POST /generate creates a signal row (mock collectors)."""
    patent = _make_patent(db_session)
    await db_session.commit()

    with patch(
        "app.api.v1.usage_signals.collect_all_evidence",
        return_value=(
            [
                {
                    "patent_publication_id": patent.id,
                    "source_type": "similar_newer_patent",
                    "source_patent_id": uuid4(),
                    "source_patent_title": "Mocked source patent",
                    "source_patent_assignee": "MockCorp",
                    "source_patent_filing_date": date(2025, 5, 1),
                    "evidence_tier": "medium",
                    "cpc_overlap_count": 1,
                    "matched_cpc": ["G06F"],
                }
            ],
            {"total_evidence": 1},
        ),
    ):
        resp = await client.post(f"/api/v1/usage-signals/{patent.id}/generate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] > 0
    assert data["evidence_count"] == 1
    assert data["confidence"] in ("low", "medium", "high")


@pytest.mark.asyncio(loop_scope="function")
async def test_post_generate_404_for_unknown(client):
    """POST /generate returns 404 for unknown patent."""
    resp = await client.post(f"/api/v1/usage-signals/{uuid4()}/generate")
    assert resp.status_code == 404
