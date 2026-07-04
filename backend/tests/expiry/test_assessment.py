"""Tests for expiry assessment engine and backfill task."""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.ai_models import ExpiryAssessment
from app.core.models import PatentPublication
from app.expiry.assessment import (
    compute_expiry_assessment,
    compute_expiry_opportunity_score,
)


def _make_patent(**overrides) -> PatentPublication:
    """Create a minimal PatentPublication for testing."""
    defaults = {
        "doc_id": f"USPTO:TEST{uuid4().hex[:8]}",
        "office": "USPTO",
        "publication_number": f"TEST{uuid4().hex[:6]}",
        "assignees": ["TestCorp"],
        "cpc": ["G06F"],
        "title": "Test patent",
        "abstract": "Test abstract.",
        "legal_status": "GRANTED",
        "legal_status_confidence": "estimated",
        "filing_date": date(2020, 1, 15),
        "grant_date": date(2022, 6, 1),
        "estimated_expiry_date": date(2042, 1, 15),
    }
    defaults.update(overrides)
    return PatentPublication(**defaults)


@pytest.mark.asyncio
async def test_missing_expiry_data_returns_unknown():
    """Patent with no estimated_expiry_date → status unknown, low confidence."""
    patent = _make_patent(
        estimated_expiry_date=None,
        grant_date=None,
        filing_date=None,
    )
    result = compute_expiry_assessment(patent)
    assert result["expiry_status"] == "unknown"
    assert result["expiry_status_confidence"] == "low"
    assert len(result["legal_caveats"]) >= 1
    assert any("cannot be determined" in c.lower() for c in result["legal_caveats"])


@pytest.mark.asyncio
async def test_future_expiry_returns_active_estimated():
    """Patent expiring far in the future → active_estimated."""
    far_future = date.today() + timedelta(days=365 * 10)
    patent = _make_patent(estimated_expiry_date=far_future)
    result = compute_expiry_assessment(patent)
    assert result["expiry_status"] == "active_estimated"


@pytest.mark.asyncio
async def test_expiring_soon_window():
    """Patent expiring within 3-year window → expiring_soon."""
    soon = date.today() + timedelta(days=365)  # 1 year from now
    patent = _make_patent(estimated_expiry_date=soon)
    result = compute_expiry_assessment(patent)
    assert result["expiry_status"] == "expiring_soon"
    # Should have a caveat about expiry being estimated.
    assert any("estimated" in c.lower() for c in result["legal_caveats"])


@pytest.mark.asyncio
async def test_past_expiry_without_confirmation_returns_expired_estimated():
    """Patent with past estimated_expiry_date but no confirmation → expired_estimated."""
    past = date.today() - timedelta(days=365)
    patent = _make_patent(estimated_expiry_date=past)
    result = compute_expiry_assessment(patent)
    assert result["expiry_status"] == "expired_estimated"
    # Should have the "verify with patent office" caveat.
    assert any("verify" in c.lower() for c in result["legal_caveats"])
    # Should also have maintenance data warning.
    assert any("maintenance" in c.lower() for c in result["legal_caveats"])


@pytest.mark.asyncio
async def test_lapsed_maintenance_status():
    """Patent with maintenance_status='LAPSED' → lapsed_confirmed, confirmed confidence."""
    patent = _make_patent(
        maintenance_status="LAPSED",
        estimated_expiry_date=date.today() - timedelta(days=100),
    )
    result = compute_expiry_assessment(patent)
    assert result["expiry_status"] == "lapsed_confirmed"
    assert result["maintenance_status"] == "lapsed_confirmed"
    assert result["expiry_status_confidence"] == "confirmed"


@pytest.mark.asyncio
async def test_expired_maintenance_status():
    """Patent with maintenance_status='EXPIRED' → expired_confirmed, confirmed confidence."""
    patent = _make_patent(
        maintenance_status="EXPIRED",
        estimated_expiry_date=date.today() - timedelta(days=500),
    )
    result = compute_expiry_assessment(patent)
    assert result["expiry_status"] == "expired_confirmed"
    assert result["maintenance_status"] == "expired_confirmed"
    assert result["expiry_status_confidence"] == "confirmed"


@pytest.mark.asyncio
async def test_family_risk_flagged_for_expired_patent():
    """Expired patent with family members → active family risk flagged."""
    patent = _make_patent(
        estimated_expiry_date=date.today() - timedelta(days=500),
        family_members=["US123456", "EP999999"],
        publication_number="US123456",
    )
    result = compute_expiry_assessment(patent)
    assert result["active_family_risk"] is True
    assert result["active_family_risk_reason"] is not None
    assert "family member" in result["active_family_risk_reason"].lower()
    # Caveats should include family risk warning.
    assert any("family" in c.lower() for c in result["legal_caveats"])


@pytest.mark.asyncio
async def test_no_family_risk_for_active_patent():
    """Active patent with family members → no family risk flagged (that's normal)."""
    far_future = date.today() + timedelta(days=365 * 10)
    patent = _make_patent(
        estimated_expiry_date=far_future,
        family_members=["US123456", "EP999999"],
        publication_number="US123456",
    )
    result = compute_expiry_assessment(patent)
    assert result["active_family_risk"] is False


@pytest.mark.asyncio
async def test_legal_status_confirmed_boosts_confidence():
    """legal_status_confidence='confirmed' → high confidence (with grant date)."""
    patent = _make_patent(
        legal_status_confidence="confirmed",
        estimated_expiry_date=date.today() - timedelta(days=100),
    )
    result = compute_expiry_assessment(patent)
    assert result["expiry_status_confidence"] == "high"


@pytest.mark.asyncio
async def test_no_grant_date_reduces_confidence():
    """No grant date → low confidence even with estimated_expiry_date."""
    patent = _make_patent(
        grant_date=None,
        estimated_expiry_date=date.today() + timedelta(days=365),
    )
    result = compute_expiry_assessment(patent)
    assert result["expiry_status_confidence"] == "low"


@pytest.mark.asyncio
async def test_custom_as_of_date():
    """Custom as_of_date affects the status calculation."""
    patent = _make_patent(
        estimated_expiry_date=date(2030, 6, 1),
    )
    # With as_of_date far in the future, this should appear expired.
    future_date = date(2035, 1, 1)
    result = compute_expiry_assessment(patent, as_of_date=future_date)
    assert result["expiry_status"] == "expired_estimated"


# ══════════════════════════════════════════════════════════════════════
# Backfill integration tests (use session-aware core function)
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_backfill_creates_assessments(db_session):
    """Session-aware backfill inserts ExpiryAssessment rows for un-assessed patents."""
    from app.tasks.expiry_assessments import backfill_expiry_assessments_for_session

    patent = PatentPublication(
        doc_id="USPTO:BACKFILL001",
        office="USPTO",
        publication_number="BACKFILL001",
        assignees=["BackfillCorp"],
        cpc=["H04L"],
        title="Backfill test patent",
        abstract="Testing backfill.",
        legal_status="GRANTED",
        legal_status_confidence="estimated",
        filing_date=date(2018, 1, 15),
        grant_date=date(2020, 6, 1),
        estimated_expiry_date=date.today() + timedelta(days=365),
    )
    db_session.add(patent)
    await db_session.commit()

    stats = await backfill_expiry_assessments_for_session(db_session)
    assert stats["created"] >= 1

    # Verify the assessment row exists.
    result = await db_session.execute(
        select(ExpiryAssessment).where(ExpiryAssessment.patent_publication_id == patent.id)
    )
    assessment = result.scalar_one_or_none()
    assert assessment is not None
    assert assessment.expiry_status == "expiring_soon"
    assert assessment.expiry_status_confidence in ("low", "medium")
    assert len(assessment.legal_caveats) >= 1


@pytest.mark.asyncio
async def test_backfill_is_idempotent(db_session):
    """Running backfill twice via session-aware function does not duplicate."""
    from app.tasks.expiry_assessments import backfill_expiry_assessments_for_session

    patent = PatentPublication(
        doc_id="USPTO:BACKFILL002",
        office="USPTO",
        publication_number="BACKFILL002",
        assignees=["IdemCorp"],
        cpc=["G06N"],
        title="Idempotent test",
        abstract="Testing idempotency.",
        legal_status="GRANTED",
        legal_status_confidence="estimated",
        filing_date=date(2019, 3, 1),
        grant_date=date(2021, 9, 1),
        estimated_expiry_date=date(2041, 3, 1),
    )
    db_session.add(patent)
    await db_session.commit()

    stats1 = await backfill_expiry_assessments_for_session(db_session)
    assert stats1["created"] >= 1

    # Second run: the patent already has an assessment, so created should be 0.
    stats2 = await backfill_expiry_assessments_for_session(db_session)
    assert stats2["created"] == 0

    # Exactly one row per patent.
    result = await db_session.execute(
        select(ExpiryAssessment).where(ExpiryAssessment.patent_publication_id == patent.id)
    )
    rows = result.scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_backfill_limit_parameter(db_session):
    """Session-aware backfill respects the limit parameter."""
    from app.tasks.expiry_assessments import backfill_expiry_assessments_for_session

    for i in range(3):
        patent = PatentPublication(
            doc_id=f"USPTO:LIMIT{i:03d}",
            office="USPTO",
            publication_number=f"LIMIT{i:03d}",
            assignees=["LimitCorp"],
            cpc=["A61B"],
            title=f"Limit test {i}",
            abstract="Testing limit.",
            legal_status="GRANTED",
            legal_status_confidence="estimated",
            filing_date=date(2020, 1, 1),
            grant_date=date(2022, 1, 1),
            estimated_expiry_date=date(2042, 1, 1),
        )
        db_session.add(patent)
    await db_session.commit()

    stats = await backfill_expiry_assessments_for_session(db_session, limit=2)
    assert stats["total_processed"] == 2


# ══════════════════════════════════════════════════════════════════════
# Expiry opportunity scoring tests (Sprint 2B)
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_score_expired_confirmed_scores_high():
    """Expired confirmed patent scores highest."""
    patent = _make_patent(
        maintenance_status="EXPIRED",
        estimated_expiry_date=date.today() - timedelta(days=500),
    )
    assessment = compute_expiry_assessment(patent)
    result = compute_expiry_opportunity_score(patent, assessment)
    assert result["score"] >= 15  # base minimum for expired+confirmed
    assert result["breakdown"]["status_component"] == 30


@pytest.mark.asyncio
async def test_score_unknown_scores_low():
    """Unknown status scores low."""
    patent = _make_patent(
        estimated_expiry_date=None,
        grant_date=None,
        filing_date=None,
    )
    assessment = compute_expiry_assessment(patent)
    result = compute_expiry_opportunity_score(patent, assessment)
    assert result["score"] <= 5


@pytest.mark.asyncio
async def test_score_family_risk_penalizes():
    """Active family risk reduces the score."""
    patent = _make_patent(
        estimated_expiry_date=date.today() - timedelta(days=500),
        family_members=["US123456", "EP999999"],
        publication_number="US123456",
    )
    assessment = compute_expiry_assessment(patent)
    result = compute_expiry_opportunity_score(patent, assessment)
    assert result["breakdown"]["family_risk_penalty"] >= 8


@pytest.mark.asyncio
async def test_score_no_family_risk_no_penalty():
    """No family risk means no penalty."""
    patent = _make_patent(
        estimated_expiry_date=date.today() - timedelta(days=500),
        family_members=["US123456"],
        publication_number="US123456",
    )
    assessment = compute_expiry_assessment(patent)
    result = compute_expiry_opportunity_score(patent, assessment)
    assert result["breakdown"]["family_risk_penalty"] == 0


@pytest.mark.asyncio
async def test_score_claims_text_adds_component():
    """Patents with claims text score higher."""
    patent_no_claims = _make_patent(
        estimated_expiry_date=date.today() - timedelta(days=500),
    )
    patent_with_claims = _make_patent(
        estimated_expiry_date=date.today() - timedelta(days=500),
        claims_text="1. A method comprising...",
    )
    assessment_no = compute_expiry_assessment(patent_no_claims)
    assessment_yes = compute_expiry_assessment(patent_with_claims)

    score_no = compute_expiry_opportunity_score(patent_no_claims, assessment_no)
    score_yes = compute_expiry_opportunity_score(patent_with_claims, assessment_yes)

    assert score_yes["score"] > score_no["score"]
    assert score_yes["breakdown"]["claims_component"] == 10.0
    assert score_no["breakdown"]["claims_component"] == 0.0


@pytest.mark.asyncio
async def test_backfill_includes_opportunity_score(db_session):
    """Session-aware backfill now computes and stores the expiry opportunity score."""
    from app.tasks.expiry_assessments import backfill_expiry_assessments_for_session

    patent = _make_patent(
        doc_id="USPTO:SCORE001",
        publication_number="SCORE001",
        estimated_expiry_date=date.today() - timedelta(days=500),
    )
    db_session.add(patent)
    await db_session.commit()

    stats = await backfill_expiry_assessments_for_session(db_session)
    assert stats["created"] >= 1

    result = await db_session.execute(
        select(ExpiryAssessment).where(ExpiryAssessment.patent_publication_id == patent.id)
    )
    assessment = result.scalar_one()
    assert assessment.expiry_opportunity_score is not None
    assert 0 <= assessment.expiry_opportunity_score <= 100
    assert assessment.expiry_opportunity_breakdown is not None
    assert "status_component" in assessment.expiry_opportunity_breakdown


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════
