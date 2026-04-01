"""
EPO Patent Ingestion Tasks.

Scheduled to run on Wednesdays when EPO publishes new patents.
"""

import asyncio
import logging
from datetime import date

from app.ai.scorer import PatentScorer
from app.config import settings
from app.core.exceptions import TransientIngestionError
from app.database import async_session_maker
from app.ingestion.dedup import upsert_patent
from app.ingestion.epo_client import EPOClient, get_last_wednesday
from app.ingestion.epo_normalizer import EPONormalizer
from app.tasks.celery_app import celery_app
from app.tasks.summarize import summarize_patent

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_epo.ingest_weekly_epo",
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(TransientIngestionError,),
)
def ingest_weekly_epo(self, target_date: str | None = None) -> dict:
    """
    Ingest all new EPO publications for a given Wednesday.

    Args:
        target_date: Optional date string (YYYY-MM-DD). Defaults to most recent Wednesday.

    Returns:
        Stats dict with processed, created, updated, failed counts.
    """
    if not settings.epo_ops_client_id or not settings.epo_ops_client_secret:
        logger.warning("EPO OPS credentials not configured, skipping ingestion")
        return {"skipped": True, "reason": "EPO credentials not configured"}

    if target_date:
        pub_date = date.fromisoformat(target_date)
    else:
        pub_date = get_last_wednesday()

    logger.info(f"Starting EPO ingestion for {pub_date}")

    normalizer = EPONormalizer()
    scorer = PatentScorer()

    stats = {"processed": 0, "created": 0, "updated": 0, "failed": 0, "summarization_queued": 0}
    failed_ids = []

    try:
        with EPOClient() as client:
            for raw in client.fetch_publications_by_date(pub_date):
                pub_number = raw.get("publication_number", "unknown")
                try:
                    data = normalizer.normalize_publication(raw)

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
                    failed_ids.append(pub_number)
                    logger.error(f"EPO ingest failed for {pub_number}: {exc}")

    except Exception as e:
        logger.error(f"EPO client error: {e}")
        raise TransientIngestionError(f"EPO client error: {e}") from e

    stats["processed"] = stats["created"] + stats["updated"] + stats["failed"]

    if failed_ids:
        logger.warning(f"EPO ingest completed with {len(failed_ids)} failures: {failed_ids[:10]}")

    logger.info(
        f"EPO ingestion complete for {pub_date}: "
        f"{stats['created']} created, {stats['updated']} updated, {stats['failed']} failed"
    )

    return stats


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_epo.resolve_epo_families",
    max_retries=1,
)
def resolve_epo_families(self, limit: int = 100) -> dict:
    """
    Resolve INPADOC family information for patents missing family_id.

    Args:
        limit: Maximum patents to process

    Returns:
        Stats dict with resolved/failed counts.
    """
    if not settings.epo_ops_client_id or not settings.epo_ops_client_secret:
        logger.warning("EPO OPS credentials not configured, skipping family resolution")
        return {"skipped": True, "reason": "EPO credentials not configured"}

    from app.ingestion.family_resolver import FamilyResolver

    logger.info(f"Starting family resolution (limit: {limit})")

    with EPOClient() as client:
        resolver = FamilyResolver(epo_client=client)
        stats = asyncio.run(_resolve_families_async(resolver, limit))

    logger.info(f"Family resolution complete: {stats}")
    return stats


async def _upsert_patent_async(data: dict):
    """Helper to run async upsert from sync Celery task."""
    async with async_session_maker() as session:
        return await upsert_patent(session, data)


async def _resolve_families_async(resolver, limit: int) -> dict:
    """Helper to run async family resolution."""
    async with async_session_maker() as session:
        return await resolver.batch_resolve_families(session, limit=limit)
