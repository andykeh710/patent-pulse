"""
WIPO BigQuery Ingestion Task.

Fetches WO/PCT publications from Google Patents BigQuery public dataset
and upserts into PatentPublication. Scheduled daily at 03:15 UTC.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from app.ai.scorer import PatentScorer
from app.core.exceptions import TransientIngestionError
from app.database import async_session_maker
from app.ingestion.dedup import upsert_patent
from app.ingestion.epo_normalizer import WIPONormalizer
from app.patent_sources.wipo_bigquery_provider import BigQueryWIPOProvider
from app.tasks.celery_app import celery_app
from app.tasks.summarize import summarize_patent

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_wipo_bigquery.ingest_wipo_bigquery_recent",
    max_retries=2,
    default_retry_delay=600,
    autoretry_for=(TransientIngestionError,),
)
def ingest_wipo_bigquery_recent(
    self,
    days_back: int = 7,
    max_results: int = 500,
) -> dict:
    """Ingest recent WIPO publications from BigQuery.

    Args:
        days_back: Number of past days to fetch (default 7).
        max_results: Max records to process (default 500).

    Returns:
        Stats dict with created, updated, failed counts.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)

    logger.info(
        "Starting WIPO BigQuery ingestion: %s to %s (max %d)",
        start_date, end_date, max_results,
    )

    normalizer = WIPONormalizer()
    scorer = PatentScorer()

    stats = {
        "processed": 0,
        "created": 0,
        "updated": 0,
        "failed": 0,
        "summarization_queued": 0,
    }
    failed_ids: list[str] = []

    try:
        provider = BigQueryWIPOProvider()
        for raw in provider.search_by_date_window(start_date, end_date, max_results):
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
                logger.error("WIPO BigQuery ingest failed for %s: %s", pub_number, exc)

    except Exception as e:
        logger.error("WIPO BigQuery client error: %s", e)
        raise TransientIngestionError(f"WIPO BigQuery error: {e}") from e

    stats["processed"] = stats["created"] + stats["updated"] + stats["failed"]

    if failed_ids:
        logger.warning(
            "WIPO BigQuery ingest: %d failures: %s",
            len(failed_ids), failed_ids[:10],
        )

    logger.info(
        "WIPO BigQuery ingestion complete: %d created, %d updated, %d failed",
        stats["created"], stats["updated"], stats["failed"],
    )

    return stats


async def _upsert_patent_async(data: dict):
    """Helper to run async upsert from sync Celery task."""
    async with async_session_maker() as session:
        return await upsert_patent(session, data)
