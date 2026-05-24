"""Tests for Sprint 5 citation evidence collector."""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.models import PatentPublication
from app.usage.citation_collector import (
    _compute_citation_tier,
    collect_citation_evidence,
)


def test_compute_tier_strong():
    """Recent filing + 2+ shared CPC → strong tier."""
    tier, conf, _ = _compute_citation_tier(
        filing_date=date.today() - timedelta(days=365 * 2),
        source_assignees=["Acme"],
        target_assignees=["Beta"],
        shared_cpc=2,
    )
    assert tier == "strong"
    assert conf == 0.9


def test_compute_tier_self_citation_weak():
    """Self-citation → weak tier."""
    tier, conf, extra = _compute_citation_tier(
        filing_date=date.today() - timedelta(days=365 * 3),
        source_assignees=["Acme", "Beta"],
        target_assignees=["Acme"],
        shared_cpc=3,
    )
    assert tier == "weak"
    assert extra.get("reason") == "self_citation"


def test_compute_tier_old_excluded():
    """Citation older than 20 years → excluded."""
    tier, conf, _ = _compute_citation_tier(
        filing_date=date(2000, 1, 1),
        source_assignees=["OldCorp"],
        target_assignees=["NewCorp"],
        shared_cpc=0,
    )
    assert tier == "excluded"


@pytest.mark.asyncio(loop_scope="function")
async def test_collect_returns_empty_for_no_citations(db_session):
    """Patent without forward citations returns empty list."""
    from uuid import uuid4
    uid = uuid4()
    patent = PatentPublication(
        id=uid,
        doc_id=f"USPTO:CITEST{uuid4().hex[:6]}",
        office="USPTO",
        publication_number=f"CITEST{uuid4().hex[:6]}",
        assignees=["Acme"],
        title="Test patent",
        legal_status="GRANTED",
        citations_forward=[],
    )
    db_session.add(patent)
    await db_session.commit()

    result = await collect_citation_evidence(db_session, uid)
    assert result == []


@pytest.mark.asyncio(loop_scope="function")
async def test_collect_assigns_tiers_correctly(db_session):
    """Collector assigns tiers based on age + CPC overlap + self-citation."""
    target_id = uuid4()
    target = PatentPublication(
        id=target_id,
        doc_id="USPTO:TARGET01",
        office="USPTO",
        publication_number="TARGET01",
        assignees=["TargetCorp"],
        cpc=["G06F", "H04L"],
        title="Target patent",
        legal_status="GRANTED",
        filing_date=date(2015, 1, 1),
        grant_date=date(2018, 1, 1),
        citations_forward=["USPTO:SOURCE01", "USPTO:SOURCE02"],
    )
    # Strong: recent, 2+ shared CPC, different assignee.
    source1 = PatentPublication(
        id=uuid4(),
        doc_id="USPTO:SOURCE01",
        office="USPTO",
        publication_number="SOURCE01",
        assignees=["OtherCorp"],
        cpc=["G06F", "H04L", "G06T"],
        title="Source patent 1",
        legal_status="GRANTED",
        filing_date=date(2022, 6, 1),
    )
    # Weak: self-citation (shared assignee).
    source2 = PatentPublication(
        id=uuid4(),
        doc_id="USPTO:SOURCE02",
        office="USPTO",
        publication_number="SOURCE02",
        assignees=["TargetCorp"],
        cpc=["G06F"],
        title="Source patent 2",
        legal_status="GRANTED",
        filing_date=date(2023, 1, 1),
    )
    db_session.add(target)
    db_session.add(source1)
    db_session.add(source2)
    await db_session.commit()

    result = await collect_citation_evidence(db_session, target_id)
    assert len(result) == 2

    tiers = {r["source_patent_doc_id"]: r["evidence_tier"] for r in result}
    assert tiers.get("USPTO:SOURCE01") == "strong"
    assert tiers.get("USPTO:SOURCE02") == "weak"


@pytest.mark.asyncio(loop_scope="function")
async def test_collect_self_citation_detected(db_session):
    """Self-citation identified when assignees overlap."""
    target_id = uuid4()
    target = PatentPublication(
        id=target_id,
        doc_id="USPTO:SELFCITE01",
        office="USPTO",
        publication_number="SELFCITE01",
        assignees=["SelfCorp"],
        cpc=["G06F"],
        title="Self-citing target",
        legal_status="GRANTED",
        citations_forward=["USPTO:SELFSRC01"],
    )
    source = PatentPublication(
        id=uuid4(),
        doc_id="USPTO:SELFSRC01",
        office="USPTO",
        publication_number="SELFSRC01",
        assignees=["SelfCorp"],
        cpc=["G06F"],
        title="Self-citing source",
        legal_status="GRANTED",
        filing_date=date.today(),
    )
    db_session.add(target)
    db_session.add(source)
    await db_session.commit()

    result = await collect_citation_evidence(db_session, target_id)
    assert len(result) == 1
    assert result[0]["evidence_tier"] == "weak"
