"""Tests for async citation fetcher (Sprint 6.5)."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.core.models import PatentPublication
from app.ingestion.citation_fetch import fetch_forward_citations


@pytest.mark.asyncio(loop_scope="function")
async def test_fetch_populates_citations(db_session):
    """Happy path: patent with empty citations_forward gets populated."""
    patent = PatentPublication(
        doc_id="USPTO:cit-test-1",
        publication_number="TEST001",
        office="USPTO",
        title="Test Patent",
        assignees=["TestCo"],
        cpc=["G06F"],
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    assert patent.citations_forward == []

    with patch("app.ingestion.citation_fetch._fetch_from_uspto") as mock_fetch:
        mock_fetch.return_value = ["USPTO:1111111", "USPTO:2222222", "USPTO:3333333"]
        count = await fetch_forward_citations(db_session, patent.id)

    assert count == 3
    await db_session.refresh(patent)
    assert patent.citations_forward == ["USPTO:1111111", "USPTO:2222222", "USPTO:3333333"]


@pytest.mark.asyncio(loop_scope="function")
async def test_idempotent_skips_already_populated(db_session):
    """Second call on already-populated patent returns 0."""
    patent = PatentPublication(
        doc_id="USPTO:cit-test-2",
        publication_number="TEST002",
        office="USPTO",
        title="Already Populated",
        assignees=["TestCo"],
        cpc=["G06F"],
        citations_forward=["USPTO:existing"],
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    count = await fetch_forward_citations(db_session, patent.id)
    assert count == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_returns_zero_for_missing_patent(db_session):
    """Returns 0 when patent_id doesn't exist."""
    count = await fetch_forward_citations(db_session, uuid4())
    assert count == 0
