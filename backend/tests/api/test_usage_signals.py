"""Tests for Sprint 5 usage signals API endpoints."""
from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.ai_models import PatentUsageSignals, UsageEvidence
from app.core.models import PatentPublication


async def _make_patent(db_session, **overrides):
    """Create a minimal patent for testing. Flushes immediately so child
    rows can reference the patent via FK without ordering errors.
    """
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
    await db_session.flush()
    return patent


async def _make_signal(db_session, patent_id):
    """Create a signal row for a patent (flushes immediately)."""
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
    await db_session.flush()
    return signal


@pytest.mark.asyncio(loop_scope="function")
async def test_get_usage_signals_404_for_unknown(client):
    """GET returns 404 for unknown patent_id."""
    fake_id = str(uuid4())
    resp = await client.get(f"/api/v1/usage-signals/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio(loop_scope="function")
async def test_get_usage_signals_returns_existing(client, db_session):
    """GET returns signal row when assessment exists."""
    patent = await _make_patent(db_session)
    await _make_signal(db_session, patent.id)

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


@pytest.mark.asyncio(loop_scope="function")
async def test_post_generate_creates_signal(client, db_session):
    """POST /generate creates a signal row (mock collectors).

    The mock evidence must reference a real source_patent_id because
    usage_evidence.source_patent_id is a FK to patent_publications.
    """
    patent = await _make_patent(db_session)
    source_patent = await _make_patent(db_session)
    await db_session.commit()

    with patch(
        "app.api.v1.usage_signals.collect_all_evidence",
        return_value=(
            [
                {
                    "patent_publication_id": patent.id,
                    "source_type": "similar_newer_patent",
                    "source_patent_id": source_patent.id,
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


# ── Sprint 5 Chunk 9: narrative endpoint tests ───────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_post_narrative_400_below_threshold(client, db_session):
    """POST /narrative returns 400 when score is below the threshold (20)."""
    patent = await _make_patent(db_session)
    low_signal = PatentUsageSignals(
        patent_publication_id=patent.id,
        usage_signal_score=10,  # below threshold
        usage_signal_confidence="low",
        evidence_count=1,
        has_self_citation_risk=False,
    )
    db_session.add(low_signal)
    await db_session.commit()

    resp = await client.post(f"/api/v1/usage-signals/{patent.id}/narrative")
    assert resp.status_code == 400
    assert "minimum" in resp.json()["detail"].lower()


@pytest.mark.asyncio(loop_scope="function")
async def test_post_narrative_cache_hit_returns_same_result(client, db_session):
    """When narrative_artifact_id is set on the signal row, POST /narrative
    returns the cached artifact content with cached=True — no regeneration.
    Two consecutive calls return identical content.
    """
    from app.core.ai_models import AIArtifact

    patent = await _make_patent(db_session)
    artifact_id = uuid4()

    cached_content = {
        "summary": "Cached narrative summary about evidence overlap.",
        "evidence_summary": "Two pieces of evidence indicate technical overlap.",
        "market_categories": ["G06F"],
        "related_companies": ["Acme"],
        "limitations": [
            "Evidence is patent-based only — no product-level verification has been performed.",
        ],
    }
    db_session.add(
        AIArtifact(
            id=artifact_id,
            artifact_type="usage_signal_narrative",
            model="claude-sonnet-4-20250514",
            prompt_name="usage_signal_narrative",
            prompt_version=1,
            prompt_hash="cache_test_prompt_hash",
            input_hash="cache_test_input_hash",
            status="complete",
            content_json=cached_content,
        )
    )
    signal = await _make_signal(db_session, patent.id)
    signal.usage_signal_score = 60
    signal.narrative_artifact_id = artifact_id
    await db_session.commit()

    resp1 = await client.post(f"/api/v1/usage-signals/{patent.id}/narrative")
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["cached"] is True
    assert body1["summary"] == cached_content["summary"]
    assert body1["evidence_summary"] == cached_content["evidence_summary"]
    assert body1["market_categories"] == ["G06F"]

    resp2 = await client.post(f"/api/v1/usage-signals/{patent.id}/narrative")
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2 == body1, "Second call should return identical cached content"
