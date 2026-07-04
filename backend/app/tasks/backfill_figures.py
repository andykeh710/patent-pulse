"""Celery tasks for patent figure fetching."""

from __future__ import annotations

import asyncio
from uuid import UUID

from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.backfill_figures.backfill_figures",
    max_retries=1,
    default_retry_delay=300,
)
def backfill_figures(self, limit: int = 50, priority_order: str = "briefing") -> dict:
    """Backfill figures for patents that need them.

    Args:
        limit: Max patents to process in this batch.
        priority_order: 'briefing' (prioritize surfaced patents) or
                        'recent' (newest first).

    Returns:
        Stats dict: total_processed, complete, partial, unavailable, errors.
    """
    logger.info("Starting figure backfill: limit=%d priority=%s", limit, priority_order)
    stats = asyncio.run(_backfill_async(limit, priority_order))
    logger.info("Figure backfill complete: %s", stats)
    return stats


async def _backfill_async(limit: int, priority_order: str) -> dict:
    from app.core.models import PatentPublication
    from app.ingestion.figure_fetcher import fetch_and_store_figures

    stats = {
        "total_processed": 0,
        "complete": 0,
        "partial": 0,
        "unavailable": 0,
        "errors": 0,
        "per_source": {},
    }

    async with async_session_maker() as session:
        # Build query: patents with figures_status='pending'
        query = select(PatentPublication).where(PatentPublication.figures_status == "pending")

        if priority_order == "briefing":
            # Prioritize patents surfaced in briefings/expiry radar
            query = query.where(PatentPublication.opportunity_score.isnot(None)).order_by(
                PatentPublication.opportunity_score.desc().nulls_last()
            )
        else:
            query = query.order_by(PatentPublication.publication_date.desc().nulls_last())

        query = query.limit(limit)
        result = await session.execute(query)
        patents = result.scalars().all()

        if not patents:
            logger.info("No pending patents for figure backfill")
            return stats

        logger.info("Figure backfill: %d patents to process", len(patents))

        for patent in patents:
            try:
                result_stats = await fetch_and_store_figures(session, patent)
                stats["total_processed"] += 1
                status = result_stats.get("status", "error")
                if status == "complete":
                    stats["complete"] += 1
                elif status == "partial":
                    stats["partial"] += 1
                elif status == "unavailable":
                    stats["unavailable"] += 1
                else:
                    stats["errors"] += 1

                source = result_stats.get("source", "unknown")
                stats["per_source"][source] = stats["per_source"].get(source, 0) + 1

            except Exception:
                logger.exception("Figure backfill failed for patent %s", patent.id)
                stats["errors"] += 1

        await session.commit()

    return stats


@celery_app.task(
    bind=True,
    name="app.tasks.backfill_figures.fetch_patent_figures",
    max_retries=settings.figure_retry_max_attempts,
    default_retry_delay=int(settings.figure_retry_backoff_base),
)
def fetch_patent_figures(self, patent_id: str) -> dict:
    """Fetch and store figures for a single patent.

    Intended for chaining after normalization in the ingestion pipeline.
    Retries with exponential backoff on transient failures.

    Args:
        patent_id: UUID string of the patent.
    """

    async def _run():
        from app.core.models import PatentPublication
        from app.ingestion.figure_fetcher import fetch_and_store_figures

        async with async_session_maker() as session:
            result = await session.execute(
                select(PatentPublication).where(PatentPublication.id == UUID(patent_id))
            )
            patent = result.scalar_one_or_none()
            if patent is None:
                return {"error": f"Patent {patent_id} not found"}

            stats = await fetch_and_store_figures(session, patent)
            await session.commit()
            return stats

    return asyncio.run(_run())


def compute_figure_page_url(publication_number: str, office: str) -> str | None:
    """Compute a Google Patents figure-page URL for link-out purposes.

    Args:
        publication_number: e.g. '8930995' or 'US8930995'
        office: 'USPTO', 'EPO', 'WIPO', etc.

    Returns:
        Google Patents thumbnails URL, or None for design patents (D-prefix).
    """
    clean = publication_number.strip().upper()
    # Strip any existing prefix
    for prefix in ("US", "EP", "WO", "JP", "CN", "KR", "DE", "FR", "GB"):
        if clean.startswith(prefix) and not clean.startswith(f"{prefix}D"):
            clean = clean[len(prefix) :]
            break

    office_prefix = {"USPTO": "US", "EPO": "EP", "WIPO": "WO"}.get(office, office[:2])

    # Design patents: Google Patents URL format differs
    if clean.startswith("D"):
        return None

    return f"https://patents.google.com/patent/{office_prefix}{clean}/thumbnails"
