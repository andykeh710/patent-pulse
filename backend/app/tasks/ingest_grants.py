import asyncio
import logging
from datetime import date

from app.ai.scorer import PatentScorer
from app.config import settings
from app.core.exceptions import TransientIngestionError
from app.database import async_session_maker
from app.ingestion.dedup import upsert_patent
from app.ingestion.normalizer import USPTONormalizer
from app.ingestion.uspto_client import USPTOClient, get_last_tuesday
from app.tasks.celery_app import celery_app
from app.tasks.summarize import summarize_patent

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_grants.ingest_weekly_grants",
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(TransientIngestionError,),
)
def ingest_weekly_grants(self, target_date: str | None = None) -> dict:
    """
    Ingest all new USPTO grants for a given Tuesday.

    Args:
        target_date: Optional date string (YYYY-MM-DD). Defaults to most recent Tuesday.

    Returns:
        Stats dict with processed, created, updated, failed counts.
    """
    if target_date:
        grant_date = date.fromisoformat(target_date)
    else:
        grant_date = get_last_tuesday()

    logger.info(f"Starting grant ingestion for {grant_date}")

    client = USPTOClient(api_key=settings.uspto_api_key)
    normalizer = USPTONormalizer()
    scorer = PatentScorer()

    stats = {"processed": 0, "created": 0, "updated": 0, "failed": 0, "summarization_queued": 0}
    failed_ids = []

    for raw in client.fetch_grants_by_date(grant_date):
        patent_number = raw.get("patent_number", "unknown")
        try:
            data = normalizer.normalize_grant(raw)

            score, breakdown = scorer.score_dict(data)
            data["interesting_score"] = score
            data["score_breakdown"] = breakdown

            record, created = asyncio.run(_upsert_patent_async(data))

            if created:
                stats["created"] += 1
                summarize_patent.delay(str(record.id))
                stats["summarization_queued"] += 1
            else:
                stats["updated"] += 1

        except Exception as exc:
            stats["failed"] += 1
            failed_ids.append(patent_number)
            logger.error(f"Grant ingest failed for {patent_number}: {exc}")

    stats["processed"] = stats["created"] + stats["updated"] + stats["failed"]

    if failed_ids:
        logger.warning(f"Grant ingest completed with {len(failed_ids)} failures: {failed_ids[:10]}")

    logger.info(
        f"Grant ingestion complete for {grant_date}: "
        f"{stats['created']} created, {stats['updated']} updated, {stats['failed']} failed"
    )

    return stats


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_grants.ingest_grants_range",
    max_retries=1,
)
def ingest_grants_range(self, start_date: str, end_date: str) -> dict:
    """
    Ingest grants for a date range. Useful for backfill.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Aggregated stats dict.
    """
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    logger.info(f"Starting grant range ingestion from {start} to {end}")

    client = USPTOClient(api_key=settings.uspto_api_key)
    normalizer = USPTONormalizer()
    scorer = PatentScorer()

    stats = {"processed": 0, "created": 0, "updated": 0, "failed": 0}

    for raw in client.fetch_grants_range(start, end):
        try:
            data = normalizer.normalize_grant(raw)
            score, breakdown = scorer.score_dict(data)
            data["interesting_score"] = score
            data["score_breakdown"] = breakdown

            record, created = asyncio.run(_upsert_patent_async(data))

            stats["created" if created else "updated"] += 1
        except Exception as exc:
            stats["failed"] += 1
            logger.error(f"Grant ingest failed: {exc}")

    stats["processed"] = stats["created"] + stats["updated"] + stats["failed"]
    logger.info(f"Grant range ingestion complete: {stats}")

    return stats


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_grants.ingest_expiry_window_grants",
    max_retries=1,
)
def ingest_expiry_window_grants(self) -> dict:
    """
    Backfill USPTO grants from 2006-2011.
    These have filing dates ~2004-2009, giving expiry dates ~2024-2029.
    Used to populate the 'expiring soon' content bucket.
    """
    logger.info("Starting expiry window backfill: 2006-01-01 to 2011-12-31")
    return ingest_grants_range.run("2006-01-01", "2011-12-31")


async def _upsert_patent_async(data: dict):
    """Helper to run async upsert from sync Celery task."""
    async with async_session_maker() as session:
        return await upsert_patent(session, data)
