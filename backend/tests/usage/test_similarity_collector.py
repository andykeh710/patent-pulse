"""Tests for Sprint 5 similarity evidence collector."""
from datetime import date
from uuid import uuid4

import pytest

from app.core.models import PatentPublication
from app.usage.similarity_collector import (
    _compute_similarity_tier,
    collect_similar_evidence,
)


def test_compute_similarity_tier_strong():
    """≥0.85 similarity + ≥1 shared CPC → strong."""
    tier, conf = _compute_similarity_tier(
        similarity=0.88,
        shared_cpc=2,
        source_assignees=["Acme"],
        target_assignees=["Beta"],
    )
    assert tier == "strong"
    assert conf == 0.9


def test_compute_similarity_tier_medium():
    """≥0.75 but <0.85 → medium."""
    tier, conf = _compute_similarity_tier(
        similarity=0.78,
        shared_cpc=0,
        source_assignees=["Acme"],
        target_assignees=["Beta"],
    )
    assert tier == "medium"


def test_compute_similarity_tier_excluded():
    """<0.65 → excluded."""
    tier, conf = _compute_similarity_tier(
        similarity=0.5,
        shared_cpc=3,
        source_assignees=["Acme"],
        target_assignees=["Beta"],
    )
    assert tier == "excluded"


@pytest.mark.asyncio(loop_scope="function")
async def test_collect_returns_empty_for_no_embedding(db_session):
    """Patent without embedding returns empty list."""
    uid = uuid4()
    patent = PatentPublication(
        id=uid,
        doc_id=f"USPTO:SIMTEST{uuid4().hex[:6]}",
        office="USPTO",
        publication_number=f"SIMTEST{uuid4().hex[:6]}",
        assignees=["Acme"],
        title="Test patent",
        legal_status="GRANTED",
        embedding=None,
    )
    db_session.add(patent)
    await db_session.commit()

    result = await collect_similar_evidence(db_session, uid)
    assert result == []


@pytest.mark.asyncio(loop_scope="function")
async def test_collect_excludes_older_patents(db_session):
    """Patents filed BEFORE the source's grant_date are excluded.
    Only patents filed AFTER it qualify as "newer art" evidence (decision #7).
    """
    source_id = uuid4()
    older_id = uuid4()
    newer_id = uuid4()

    # Use a high-magnitude vector so the cosine similarity to a matching copy
    # is essentially 1.0 — well above the WEAK_SIMILARITY threshold.
    shared_embedding = [0.05] * 1536

    source = PatentPublication(
        id=source_id,
        doc_id=f"USPTO:SRC{uuid4().hex[:6]}",
        office="USPTO",
        publication_number=f"SRC{uuid4().hex[:6]}",
        assignees=["Acme"],
        cpc=["G06F"],
        title="Source patent",
        legal_status="GRANTED",
        filing_date=date(2022, 1, 1),
        grant_date=date(2024, 1, 1),
        embedding=shared_embedding,
    )
    older = PatentPublication(
        id=older_id,
        doc_id=f"USPTO:OLD{uuid4().hex[:6]}",
        office="USPTO",
        publication_number=f"OLD{uuid4().hex[:6]}",
        assignees=["Beta"],
        cpc=["G06F"],
        title="Older similar patent",
        legal_status="GRANTED",
        filing_date=date(2023, 6, 1),  # before source.grant_date (2024-01-01)
        grant_date=date(2024, 6, 1),
        embedding=shared_embedding,
    )
    newer = PatentPublication(
        id=newer_id,
        doc_id=f"USPTO:NEW{uuid4().hex[:6]}",
        office="USPTO",
        publication_number=f"NEW{uuid4().hex[:6]}",
        assignees=["Gamma"],
        cpc=["G06F"],
        title="Newer similar patent",
        legal_status="GRANTED",
        filing_date=date(2024, 6, 1),  # after source.grant_date
        grant_date=date(2025, 6, 1),
        embedding=shared_embedding,
    )
    db_session.add_all([source, older, newer])
    await db_session.commit()

    result = await collect_similar_evidence(db_session, source_id)

    returned_ids = {ev["source_patent_id"] for ev in result}
    assert newer_id in returned_ids, "Newer-than-source patent must appear in evidence"
    assert older_id not in returned_ids, "Older-than-source patent must be excluded"
    assert source_id not in returned_ids, "Source must never appear in its own evidence"
