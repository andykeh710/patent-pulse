"""
BigQuery supplemental USPTO data source.

Used as a supplemental/fallback source for patent data. The Google Patents
public dataset (patents-public-data.patents.publications) is NOT suitable as
the primary daily freshness source — it lags USPTO publication by 1-2 months.

Primary daily USPTO ingestion should use the USPTO IBD API or weekly bulk XML
files when available. This module provides BigQuery access for backfill and
supplemental queries.
"""

import asyncio
import logging
from datetime import date, timedelta

from celery.utils.log import get_task_logger

from app.ai.scorer import PatentScorer
from app.config import settings
from app.database import async_session_maker
from app.ingestion.bigquery_client import BigQueryClient
from app.ingestion.dedup import upsert_patent
from app.ingestion.normalizer import USPTONormalizer
from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)
BATCH_SIZE = 200


def ingest_from_bigquery_range(start_date: date, end_date: date) -> dict:
    """
    Fetch and ingest US patents from BigQuery for a date range.

    Normalizes, scores, and upserts every record via the existing
    USPTONormalizer + PatentScorer + upsert_patent pipeline.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        Stats dict with processed, created, updated, failed, fetched counts.
    """
    if not settings.google_cloud_project:
        return {
            "processed": 0, "created": 0, "updated": 0,
            "failed": 1, "fetched": 0,
            "error": "GOOGLE_CLOUD_PROJECT not configured",
        }

    client = BigQueryClient(project=settings.google_cloud_project)
    normalizer = USPTONormalizer()
    scorer = PatentScorer()

    stats = {"processed": 0, "created": 0, "updated": 0, "failed": 0, "fetched": 0}

    logger.info(f"BigQuery ingestion: {start_date} → {end_date}")

    batch = []
    try:
        for raw in client.fetch_us_patents(start_date, end_date):
            stats["fetched"] += 1
            try:
                # Determine kind code: B* = grant, A* = application
                pub_num = raw.get("publication_number", "")
                kind_code = pub_num[-2:] if len(pub_num) >= 2 else ""

                if kind_code.startswith("B"):
                    data = normalizer.normalize_grant(raw)
                else:
                    data = normalizer.normalize_application(raw)

                score, breakdown = scorer.score_dict(data)
                data["interesting_score"] = score
                data["score_breakdown"] = breakdown
                data["family_id"] = raw.get("family_id")

                batch.append(data)

                if len(batch) >= BATCH_SIZE:
                    r = asyncio.run(_upsert_batch(batch))
                    stats["created"] += r["created"]
                    stats["updated"] += r["updated"]
                    stats["failed"] += r["failed"]
                    stats["processed"] += len(batch)
                    logger.info(
                        f"BigQuery progress: {stats['fetched']} fetched, "
                        f"{stats['created']} new, {stats['updated']} updated"
                    )
                    batch = []

            except Exception as exc:
                stats["failed"] += 1
                logger.warning(f"Failed to process {pub_num}: {exc}")

        # Flush remaining batch
        if batch:
            r = asyncio.run(_upsert_batch(batch))
            stats["created"] += r["created"]
            stats["updated"] += r["updated"]
            stats["failed"] += r["failed"]
            stats["processed"] += len(batch)

    except Exception as exc:
        logger.error(f"BigQuery ingestion failed: {exc}", exc_info=True)
        stats["error"] = str(exc)[:500]

    logger.info(
        f"BigQuery complete: {stats['fetched']} fetched, "
        f"{stats['created']} created, {stats['updated']} updated, "
        f"{stats['failed']} failed"
    )
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
