"""
WIPO PCT Patent Ingestion Tasks.

Scheduled to run on Thursdays when WIPO publishes PCT applications.

Note: WIPO PatentScope terms prohibit bulk scraping. This task is designed
for targeted discovery of high-value PCT applications only.
"""

import asyncio
import logging
from datetime import date

from app.ai.scorer import PatentScorer
from app.core.exceptions import TransientIngestionError
from app.database import async_session_maker
from app.ingestion.dedup import upsert_patent
from app.ingestion.epo_normalizer import WIPONormalizer
from app.ingestion.wipo_client import WIPOClient, get_last_thursday
from app.tasks.celery_app import celery_app
from app.tasks.summarize import summarize_patent

logger = logging.getLogger(__name__)

DEFAULT_MAX_RESULTS = 100


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_wipo.ingest_weekly_pct",
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(TransientIngestionError,),
)
def ingest_weekly_pct(
    self,
    target_date: str | None = None,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> dict:
    """
    Ingest PCT applications for a given Thursday.

    Note: Limited to targeted discovery per WIPO terms of use.

    Args:
        target_date: Optional date string (YYYY-MM-DD). Defaults to most recent Thursday.
        max_results: Maximum number of applications to fetch (default 100).

    Returns:
        Stats dict with processed, created, updated, failed counts.
    """
    if target_date:
        pub_date = date.fromisoformat(target_date)
    else:
        pub_date = get_last_thursday()

    logger.info(f"Starting PCT ingestion for {pub_date} (max: {max_results})")

    normalizer = WIPONormalizer()
    scorer = PatentScorer()

    stats = {"processed": 0, "created": 0, "updated": 0, "failed": 0, "summarization_queued": 0}
    failed_ids = []

    try:
        with WIPOClient() as client:
            for raw in client.fetch_pct_by_week(pub_date, max_results=max_results):
                pub_number = raw.get("publication_number", "unknown")
                try:
                    data = normalizer.normalize_pct_application(raw)

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
                    logger.error(f"PCT ingest failed for {pub_number}: {exc}")

    except Exception as e:
        logger.error(f"WIPO client error: {e}")
        raise TransientIngestionError(f"WIPO client error: {e}") from e

    stats["processed"] = stats["created"] + stats["updated"] + stats["failed"]

    if failed_ids:
        logger.warning(f"PCT ingest completed with {len(failed_ids)} failures: {failed_ids[:10]}")

    logger.info(
        f"PCT ingestion complete for {pub_date}: "
        f"{stats['created']} created, {stats['updated']} updated, {stats['failed']} failed"
    )

    return stats


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_wipo.fetch_pct_publication",
)
def fetch_pct_publication(self, publication_number: str) -> dict:
    """
    Fetch a specific PCT publication on demand.

    Args:
        publication_number: WO publication number (e.g., "WO2024001234")

    Returns:
        Processed patent data or error info.
    """
    logger.info(f"Fetching PCT publication: {publication_number}")

    normalizer = WIPONormalizer()
    scorer = PatentScorer()

    try:
        with WIPOClient() as client:
            raw = client.fetch_pct_publication(publication_number)

            if raw.get("parse_error"):
                return {"error": raw["parse_error"]}

            data = normalizer.normalize_pct_application(raw)

            score, breakdown = scorer.score_dict(data)
            data["interesting_score"] = score
            data["score_breakdown"] = breakdown

            record, created = asyncio.run(_upsert_patent_async(data))

            if created:
                summarize_patent.delay(str(record.id))

            return {
                "status": "success",
                "created": created,
                "patent_id": str(record.id),
                "doc_id": record.doc_id,
            }

    except Exception as e:
        logger.error(f"Failed to fetch PCT publication {publication_number}: {e}")
        return {"error": str(e)}


async def _upsert_patent_async(data: dict):
    """Helper to run async upsert from sync Celery task."""
    async with async_session_maker() as session:
        return await upsert_patent(session, data)
