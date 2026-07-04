"""
Historical citation backfill task (Sprint 6.5).

Fetches forward citations for patents that have empty citations_forward.
Idempotent: skips already-populated patents. Rate-limited at 1 call/sec
(enforced inside fetch_forward_citations from S65-2).

Throughput: ~600 patents/hr (limit=50 every 5 min).
Full 54K corpus → ~90 hours wall-clock.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import cast, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PatentPublication
from app.database import async_session_maker
from app.ingestion.citation_fetch import fetch_forward_citations
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.backfill_citations.batch_backfill_citations",
    max_retries=1,
)
def batch_backfill_citations(self, limit: int = 50) -> dict:
    logger.info("Starting citation backfill (limit=%d)", limit)

    from app.database import engine as _engine

    async def _run_and_dispose():
        try:
            return await _batch_backfill_async(limit=limit)
        finally:
            await _engine.dispose()

    try:
        stats = asyncio.run(_run_and_dispose())
    except Exception as e:
        logger.error("Citation backfill failed: %s", e)
        stats = {"status": "failed", "error": str(e)}

    logger.info("Citation backfill complete: %s", stats)
    return stats


async def _batch_backfill_async(
    *,
    limit: int,
    session: AsyncSession | None = None,
) -> dict:
    """Backfill citations. Uses provided session or creates one (S6-9 pattern)."""
    if session is not None:
        return await _backfill_with_session(session, limit)

    async with async_session_maker() as s:
        return await _backfill_with_session(s, limit)


async def _backfill_with_session(
    session: AsyncSession,
    limit: int,
) -> dict:
    stats = {"processed": 0, "populated": 0, "skipped": 0, "errors": 0}

    result = await session.execute(
        select(PatentPublication)
        .where(
            or_(
                PatentPublication.citations_forward.is_(None),
                PatentPublication.citations_forward == cast([], JSONB),
            )
        )
        .order_by(PatentPublication.opportunity_score.desc().nulls_last())
        .limit(limit)
    )
    patents = result.scalars().all()

    if not patents:
        logger.info("No patents found needing citation backfill")
        return stats

    for patent in patents:
        try:
            added = await fetch_forward_citations(session, patent.id)
            stats["processed"] += 1
            if added > 0:
                stats["populated"] += 1
            else:
                stats["skipped"] += 1
        except Exception as e:
            logger.error("Error on patent %s: %s", patent.doc_id, e)
            stats["errors"] += 1
            continue

    return stats
