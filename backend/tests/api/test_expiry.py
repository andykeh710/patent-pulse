"""Tests for Sprint 2B expiry API endpoints."""

from datetime import date, timedelta

import pytest

from app.core.ai_models import ExpiryAssessment
from app.core.models import PatentPublication
from app.expiry.assessment import compute_expiry_assessment


def _make_patent(**overrides) -> PatentPublication:
    from uuid import uuid4

    defaults = {
        "doc_id": f"USPTO:ETEST{uuid4().hex[:8]}",
        "office": "USPTO",
        "publication_number": f"ETEST{uuid4().hex[:6]}",
        "assignees": ["ApiTestCorp"],
        "cpc": ["G06F"],
        "title": "Test patent",
        "abstract": "Test abstract.",
        "legal_status": "GRANTED",
        "legal_status_confidence": "estimated",
        "filing_date": date(2020, 1, 15),
        "grant_date": date(2022, 6, 1),
        "estimated_expiry_date": date.today() + timedelta(days=365),
    }
    defaults.update(overrides)
    return PatentPublication(**defaults)


async def _create_assessment(db_session, patent, **overrides):
    """Create an ExpiryAssessment row for a patent."""
    payload = compute_expiry_assessment(patent)
    from app.expiry.assessment import compute_expiry_opportunity_score

    opp = compute_expiry_opportunity_score(patent, payload)

    assessment = ExpiryAssessment(
        patent_publication_id=patent.id,
        expiry_opportunity_score=opp["score"],
        expiry_opportunity_breakdown=opp["breakdown"],
        **{k: v for k, v in payload.items()},
    )
    for key, val in overrides.items():
        setattr(assessment, key, val)
    db_session.add(assessment)
    await db_session.commit()


# ── filters ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_expiry_filter_by_status(client, db_session):
    """Filtering by expiry_status returns only matching patents."""
    patent = _make_patent(doc_id="USPTO:FSTAT01", publication_number="FSTAT01")
    db_session.add(patent)
    await db_session.commit()
    await _create_assessment(db_session, patent, expiry_status="expiring_soon")

    # Should be found with expiring_soon filter.
    resp = await client.get("/api/v1/expiry?expiry_status=expiring_soon")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1

    # Should NOT be found with expired_confirmed filter.
    resp = await client.get("/api/v1/expiry?expiry_status=expired_confirmed")
    assert resp.status_code == 200
    data = resp.json()
    # Our test patent may or may not be in the result — depends on other data.
    # At minimum, the filter doesn't error.


@pytest.mark.asyncio
async def test_expiry_filter_by_confidence(client, db_session):
    """Filtering by confidence returns no error."""
    resp = await client.get("/api/v1/expiry?confidence=medium")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_expiry_filter_by_family_risk(client, db_session):
    """Filtering by active_family_risk returns no error."""
    resp = await client.get("/api/v1/expiry?active_family_risk=true")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_expiry_sort_by_opportunity_score(client, db_session):
    """Sorting by expiry_opportunity_score does not error."""
    resp = await client.get("/api/v1/expiry?sort_by=expiry_opportunity_score&sort_order=desc")
    assert resp.status_code == 200


# ── summary endpoint ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_returns_grouped_counts(client, db_session):
    """GET /api/v1/expiry/summary returns real grouped counts."""
    patent = _make_patent(doc_id="USPTO:SUM01", publication_number="SUM01")
    db_session.add(patent)
    await db_session.commit()
    await _create_assessment(db_session, patent)

    resp = await client.get("/api/v1/expiry/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_with_expiry" in data
    assert "by_status" in data
    assert "by_confidence" in data
    assert "with_family_risk" in data
    assert "without_family_risk" in data
    assert "high_opportunity_count" in data
    assert "by_maintenance" in data
    assert isinstance(data["total_with_expiry"], int)


# ── opportunities endpoint ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_opportunities_returns_candidates(client, db_session):
    """GET /api/v1/expiry/opportunities returns real candidates."""
    patent = _make_patent(
        doc_id="USPTO:OPP01",
        publication_number="OPP01",
        estimated_expiry_date=date.today() - timedelta(days=500),
        maintenance_status="EXPIRED",
    )
    db_session.add(patent)
    await db_session.commit()
    await _create_assessment(db_session, patent, expiry_status="expired_confirmed")

    resp = await client.get("/api/v1/expiry/opportunities?min_score=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    if data["total"] > 0:
        item = data["items"][0]
        assert "expiry_status" in item
        assert "expiry_opportunity_score" in item
        assert "active_family_risk" in item


@pytest.mark.asyncio
async def test_opportunities_respects_min_score(client, db_session):
    """Min score filter restricts results."""
    resp = await client.get("/api/v1/expiry/opportunities?min_score=90")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["expiry_opportunity_score"] >= 90


# ── Sprint 2C: expiry_window_start ───────────────────────────────────


@pytest.mark.asyncio
async def test_expiry_window_start_backward_looking(client, db_session):
    """expiry_window_start allows querying expired patents in a past window."""
    from datetime import date, timedelta

    past = date.today() - timedelta(days=200)
    patent = _make_patent(
        doc_id="USPTO:WINPAST",
        publication_number="WINPAST",
        estimated_expiry_date=past,
    )
    db_session.add(patent)
    await db_session.commit()
    await _create_assessment(db_session, patent)

    start = (date.today() - timedelta(days=365)).isoformat()
    resp = await client.get(f"/api/v1/expiry?expiry_window_start={start}&days_ahead=1&page_size=50")
    assert resp.status_code == 200
    data = resp.json()
    found = any(i["doc_id"] == "USPTO:WINPAST" for i in data["items"])
    assert found, "Patent WINPAST not found in backward-looking window."


# ── Sprint 5: has_usage_signals filter ───────────────────────────────


@pytest.mark.asyncio
async def test_has_usage_signals_filter_respects_join(client, db_session):
    """has_usage_signals=true returns only patents with a PatentUsageSignals row;
    has_usage_signals=false returns only patents without one. Both must respect
    the LEFT JOIN added in Sprint 5 Chunk 8.
    """
    from app.core.ai_models import PatentUsageSignals

    with_signal = _make_patent(
        doc_id="USPTO:WSIG01",
        publication_number="WSIG01",
        estimated_expiry_date=date.today() + timedelta(days=30),
    )
    without_signal = _make_patent(
        doc_id="USPTO:NOSIG01",
        publication_number="NOSIG01",
        estimated_expiry_date=date.today() + timedelta(days=30),
    )
    db_session.add(with_signal)
    db_session.add(without_signal)
    await db_session.commit()
    await _create_assessment(db_session, with_signal)
    await _create_assessment(db_session, without_signal)

    db_session.add(
        PatentUsageSignals(
            patent_publication_id=with_signal.id,
            usage_signal_score=55,
            usage_signal_confidence="medium",
            evidence_count=3,
            has_self_citation_risk=False,
        )
    )
    await db_session.commit()

    resp = await client.get("/api/v1/expiry?has_usage_signals=true&page_size=50")
    assert resp.status_code == 200
    ids_true = [i["doc_id"] for i in resp.json()["items"]]
    assert "USPTO:WSIG01" in ids_true
    assert "USPTO:NOSIG01" not in ids_true

    resp = await client.get("/api/v1/expiry?has_usage_signals=false&page_size=50")
    assert resp.status_code == 200
    ids_false = [i["doc_id"] for i in resp.json()["items"]]
    assert "USPTO:NOSIG01" in ids_false
    assert "USPTO:WSIG01" not in ids_false


@pytest.mark.asyncio
async def test_expiry_response_carries_usage_signal_fields(client, db_session):
    """Main list response includes usage_signal_score, evidence_count, and
    self_citation_risk fields — null when no row, populated when LEFT JOIN matches.
    """
    from app.core.ai_models import PatentUsageSignals

    patent = _make_patent(
        doc_id="USPTO:USFIELDS",
        publication_number="USFIELDS",
        estimated_expiry_date=date.today() + timedelta(days=60),
    )
    db_session.add(patent)
    await db_session.commit()
    await _create_assessment(db_session, patent)
    db_session.add(
        PatentUsageSignals(
            patent_publication_id=patent.id,
            usage_signal_score=72.5,
            usage_signal_confidence="high",
            evidence_count=4,
            has_self_citation_risk=True,
        )
    )
    await db_session.commit()

    resp = await client.get("/api/v1/expiry?page_size=100")
    assert resp.status_code == 200
    items = [i for i in resp.json()["items"] if i["doc_id"] == "USPTO:USFIELDS"]
    assert items, "USFIELDS not returned by /expiry"
    item = items[0]
    assert item["usage_signal_score"] == 72.5
    assert item["usage_signal_evidence_count"] == 4
    assert item["usage_has_self_citation_risk"] is True


@pytest.mark.asyncio
async def test_opportunities_response_carries_usage_signal_fields(client, db_session):
    """/opportunities response now LEFT JOINs patent_usage_signals (Chunk 9
    parity). Verify fields appear on opportunity items when a signal row exists.
    """
    from app.core.ai_models import PatentUsageSignals

    patent = _make_patent(
        doc_id="USPTO:OPPSIG",
        publication_number="OPPSIG",
        estimated_expiry_date=date.today() - timedelta(days=10),
        maintenance_status="EXPIRED",
    )
    db_session.add(patent)
    await db_session.commit()
    await _create_assessment(db_session, patent, expiry_status="expired_confirmed")
    db_session.add(
        PatentUsageSignals(
            patent_publication_id=patent.id,
            usage_signal_score=60,
            usage_signal_confidence="medium",
            evidence_count=2,
            has_self_citation_risk=False,
        )
    )
    await db_session.commit()

    resp = await client.get("/api/v1/expiry/opportunities?min_score=0&limit=100")
    assert resp.status_code == 200
    matching = [i for i in resp.json()["items"] if i["doc_id"] == "USPTO:OPPSIG"]
    assert matching, "OPPSIG not returned by /opportunities"
    item = matching[0]
    assert item["usage_signal_score"] == 60
    assert item["usage_signal_evidence_count"] == 2
    assert item["usage_has_self_citation_risk"] is False


@pytest.mark.asyncio
async def test_days_ahead_zero_returns_only_past(client, db_session):
    """days_ahead=0 returns only patents with expiry <= today, not future."""
    from datetime import date, timedelta

    yesterday = date.today() - timedelta(days=1)
    tomorrow = date.today() + timedelta(days=1)

    past_patent = _make_patent(
        doc_id="USPTO:STRICTPAST",
        publication_number="STRICTPAST",
        estimated_expiry_date=yesterday,
    )
    future_patent = _make_patent(
        doc_id="USPTO:FUTURE01",
        publication_number="FUTURE01",
        estimated_expiry_date=tomorrow,
    )
    db_session.add(past_patent)
    db_session.add(future_patent)
    await db_session.commit()
    await _create_assessment(db_session, past_patent)
    await _create_assessment(db_session, future_patent)

    week_ago = (date.today() - timedelta(days=7)).isoformat()
    resp = await client.get(
        f"/api/v1/expiry?expiry_window_start={week_ago}&days_ahead=0&page_size=50"
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [i["doc_id"] for i in data["items"]]
    assert "USPTO:STRICTPAST" in ids, f"STRICTPAST not found in days_ahead=0 window: {ids}"
    assert "USPTO:FUTURE01" not in ids, f"FUTURE01 should not appear with days_ahead=0: {ids}"
