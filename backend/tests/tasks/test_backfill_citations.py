"""Tests for citation backfill task (Sprint 6.5)."""
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.core.models import PatentPublication


@pytest.mark.asyncio(loop_scope="function")
async def test_backfill_populates_empty_patents(db_session):
    """3 patents with empty citations → all processed and populated."""
    patent1 = PatentPublication(
        doc_id="USPTO:bf-1", publication_number="BF001", office="USPTO",
        title="P1", assignees=["A"], cpc=["G06F"], opportunity_score=10,
    )
    patent2 = PatentPublication(
        doc_id="USPTO:bf-2", publication_number="BF002", office="USPTO",
        title="P2", assignees=["B"], cpc=["G06F"], opportunity_score=20,
    )
    patent3 = PatentPublication(
        doc_id="USPTO:bf-3", publication_number="BF003", office="USPTO",
        title="P3", assignees=["C"], cpc=["G06F"], opportunity_score=30,
    )
    db_session.add_all([patent1, patent2, patent3])
    await db_session.commit()

    from app.tasks.backfill_citations import _batch_backfill_async
    with patch("app.tasks.backfill_citations.fetch_forward_citations") as mock_fetch:
        mock_fetch.return_value = 5  # 5 citations found
        stats = await _batch_backfill_async(limit=10, session=db_session)

    assert stats["processed"] == 3
    assert stats["populated"] == 3
    assert stats["errors"] == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_backfill_skips_already_populated(db_session):
    """Patent with citations_forward already set → counted as skipped."""
    patent = PatentPublication(
        doc_id="USPTO:bf-skip", publication_number="BFSKIP", office="USPTO",
        title="Skip", assignees=["S"], cpc=["G06F"],
        citations_forward=["USPTO:existing"],
    )
    db_session.add(patent)
    await db_session.commit()

    from app.tasks.backfill_citations import _batch_backfill_async
    stats = await _batch_backfill_async(limit=10, session=db_session)

    assert stats["processed"] == 0
    assert stats["skipped"] == 0  # never fetched — not in the query


@pytest.mark.asyncio(loop_scope="function")
async def test_backfill_handles_fetch_error(db_session):
    """Mocked fetch raises → error counted, task continues."""
    patent = PatentPublication(
        doc_id="USPTO:bf-err", publication_number="BFERR", office="USPTO",
        title="Err", assignees=["E"], cpc=["G06F"],
    )
    db_session.add(patent)
    await db_session.commit()

    from app.tasks.backfill_citations import _batch_backfill_async
    with patch("app.tasks.backfill_citations.fetch_forward_citations") as mock_fetch:
        mock_fetch.side_effect = RuntimeError("SDK crash")
        stats = await _batch_backfill_async(limit=10, session=db_session)

    assert stats["processed"] == 0  # fetch failed before increment
    assert stats["errors"] == 1
    assert stats["populated"] == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_backfill_respects_limit(db_session):
    """limit=2 caps the batch size."""
    for i in range(5):
        patent = PatentPublication(
            doc_id=f"USPTO:bf-limit-{i}", publication_number=f"BFL{i}", office="USPTO",
            title=f"P{i}", assignees=["X"], cpc=["G06F"],
        )
        db_session.add(patent)
    await db_session.commit()

    from app.tasks.backfill_citations import _batch_backfill_async
    with patch("app.tasks.backfill_citations.fetch_forward_citations") as mock_fetch:
        mock_fetch.return_value = 2
        stats = await _batch_backfill_async(limit=2, session=db_session)

    assert stats["processed"] == 2
    assert stats["populated"] == 2
