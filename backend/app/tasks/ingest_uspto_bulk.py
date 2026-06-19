"""
Celery tasks for USPTO bulk data ingestion.

Weekly grant (Tuesday) and application (Thursday) ingestion using
official USPTO bulk XML files as the authoritative source.
"""

import asyncio
import logging
from datetime import date, timedelta

from celery.utils.log import get_task_logger

from app.ai.scorer import PatentScorer
from app.config import settings
from app.database import async_session_maker
from app.ingestion.dedup import upsert_patent
from app.ingestion.normalizer import USPTONormalizer
from app.ingestion.uspto_bulk_client import USPTOBulkClient
from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)
BATCH_SIZE = 200


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_uspto_bulk.ingest_grant_week",
    max_retries=1,
)
def ingest_grant_week(self, issue_date: str) -> dict:
    """
    Ingest USPTO patent grants for a specific Tuesday issue date.

    Args:
        issue_date: Grant issue date as YYYY-MM-DD string.

    Returns:
        Stats dict with fetched, created, updated, failed counts.
    """
    target = date.fromisoformat(issue_date)
    return _ingest_week("grant", target)


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_uspto_bulk.ingest_application_week",
    max_retries=1,
)
def ingest_application_week(self, publication_date: str) -> dict:
    """
    Ingest USPTO published applications for a specific Thursday date.

    Args:
        publication_date: Publication date as YYYY-MM-DD string.

    Returns:
        Stats dict with fetched, created, updated, failed counts.
    """
    target = date.fromisoformat(publication_date)
    return _ingest_week("application", target)


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_uspto_bulk.catch_up_weeks",
    max_retries=1,
)
def catch_up_weeks(self, start_date: str = "2026-05-29", end_date: str | None = None) -> dict:
    """
    Ingest all USPTO grant and application weeks in a date range.

    Args:
        start_date: Start date (inclusive) as YYYY-MM-DD.
        end_date: End date (inclusive) as YYYY-MM-DD. Defaults to today.

    Returns:
        Aggregated stats dict.
    """
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date) if end_date else date.today()

    # Find all Tuesdays (grants) and Thursdays (applications) in range
    grants_dates = _weekdays_in_range(start, end, 1)   # Tuesday = weekday 1
    apps_dates = _weekdays_in_range(start, end, 3)      # Thursday = weekday 3

    total = {"grants": {}, "applications": {}, "created": 0, "updated": 0, "failed": 0}

    for d in grants_dates:
        stats = _ingest_week("grant", d)
        total["grants"][d.isoformat()] = stats
        total["created"] += stats.get("created", 0)
        total["updated"] += stats.get("updated", 0)
        total["failed"] += stats.get("failed", 0)

    for d in apps_dates:
        stats = _ingest_week("application", d)
        total["applications"][d.isoformat()] = stats
        total["created"] += stats.get("created", 0)
        total["updated"] += stats.get("updated", 0)
        total["failed"] += stats.get("failed", 0)

    logger.info(f"Catch-up complete: {total['created']} new, {total['updated']} updated, {total['failed']} failed")
    return total


def _ingest_week(kind: str, target_date: date) -> dict:
    """Internal: ingest one week of grants or applications."""
    client = USPTOBulkClient()
    normalizer = USPTONormalizer()
    scorer = PatentScorer()

    stats = {"fetched": 0, "created": 0, "updated": 0, "failed": 0}

    fetch_fn = client.fetch_grant_week if kind == "grant" else client.fetch_application_week
    normalize_fn = normalizer.normalize_grant if kind == "grant" else normalizer.normalize_application

    batch = []
    try:
        for raw in fetch_fn(target_date):
            stats["fetched"] += 1
            try:
                data = normalize_fn(raw)
                score, breakdown = scorer.score_dict(data)
                data["interesting_score"] = score
                data["score_breakdown"] = breakdown

                batch.append(data)
                if len(batch) >= BATCH_SIZE:
                    r = asyncio.run(_upsert_batch(batch))
                    stats["created"] += r["created"]
                    stats["updated"] += r["updated"]
                    stats["failed"] += r["failed"]
                    batch = []

            except Exception as exc:
                stats["failed"] += 1
                logger.warning(f"Failed to process record: {exc}")

        if batch:
            r = asyncio.run(_upsert_batch(batch))
            stats["created"] += r["created"]
            stats["updated"] += r["updated"]
            stats["failed"] += r["failed"]

    except Exception as exc:
        logger.error(f"{kind} ingestion failed for {target_date}: {exc}", exc_info=True)
        stats["error"] = str(exc)[:500]

    logger.info(f"{kind} week {target_date}: {stats}")
    return stats


async def _upsert_batch(batch: list[dict]) -> dict:
    """Upsert a batch of normalized patent records."""
    results = {"created": 0, "updated": 0, "failed": 0}
    async with async_session_maker() as session:
        for data in batch:
            try:
                _, created = await upsert_patent(session, data)
                if created:
                    results["created"] += 1
                else:
                    results["updated"] += 1
            except Exception as exc:
                results["failed"] += 1
                logger.warning(f"Upsert failed: {exc}")
    return results


def _weekdays_in_range(start: date, end: date, weekday: int) -> list[date]:
    """Find all dates matching a weekday (0=Mon, 1=Tue, 6=Sun) in range."""
    result = []
    current = start
    while current <= end:
        if current.weekday() == weekday:
            result.append(current)
        current += timedelta(days=1)
    return result
