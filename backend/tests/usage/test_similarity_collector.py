"""Tests for Sprint 5 similarity evidence collector."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
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


@pytest.mark.xfail(
    reason="event_loop fixture contention in full suite (tracked in conftest.py). "
           "Passes in isolation. Fix post-Sprint-6.",
    strict=False,
)
@pytest.mark.asyncio(loop_scope="function")
async def test_collect_returns_empty_for_no_embedding(db_session):
    """Patent without embedding returns empty list."""
    from uuid import uuid4
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
