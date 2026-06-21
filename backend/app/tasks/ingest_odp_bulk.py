"""
ODP Bulk Dataset ingestion Celery task — V3.8C.

Uses a single async event loop to avoid RuntimeError from multiple asyncio.run().
"""

import asyncio
import logging
from datetime import date, datetime, timezone

from celery.utils.log import get_task_logger

from app.ai.scorer import PatentScorer
from app.database import async_session_maker
from app.ingestion.dedup import upsert_patent
from app.ingestion.normalizer import USPTONormalizer
from app.ingestion.uspto_odp_bulk import USPTOBulkDatasetClient
from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)
BATCH_SIZE = 200


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_odp_bulk.ingest_odp_grants_range",
    max_retries=1,
)
def ingest_odp_grants_range(self, start_date: str, end_date: str) -> dict:
    """Ingest USPTO patent grants from ODP bulk datasets."""
    return asyncio.run(
        _ingest_odp_range_async(
            "grant", date.fromisoformat(start_date), date.fromisoformat(end_date)
        )
    )


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_odp_bulk.ingest_odp_applications_range",
    max_retries=1,
)
def ingest_odp_applications_range(
    self, start_date: str, end_date: str
) -> dict:
    """Ingest USPTO published applications from ODP bulk datasets."""
    return asyncio.run(
        _ingest_odp_range_async(
            "application", date.fromisoformat(start_date), date.fromisoformat(end_date)
        )
    )


async def _ingest_odp_range_async(
    kind: str, start_date: date, end_date: date
) -> dict:
    """Core async ingestion logic — single event loop for all DB operations."""
    client = USPTOBulkDatasetClient()
    normalizer = USPTONormalizer()
    scorer = PatentScorer()

    stats = {
        "files_discovered": 0,
        "files_downloaded": 0,
        "files_failed": 0,
        "records_parsed": 0,
        "created": 0,
        "updated": 0,
        "failed": 0,
        "status": "unknown",
        "provider": "odp_bulk_dataset",
    }

    # Discover files
    if kind == "grant":
        files = client.get_grant_files(start_date, end_date)
    else:
        files = client.get_application_files(start_date, end_date)

    stats["files_discovered"] = len(files)

    if not files:
        stats["status"] = "zero_results"
        return stats

    # Process each file — all async DB ops in this single loop
    for file_info in files:
        batch = []
        for record in client.download_and_parse(file_info):
            stats["records_parsed"] += 1

            # Fix: ensure grant records have issue_date for normalizer
            if kind == "grant" and not record.get("issue_date"):
                record["issue_date"] = record.get("publication_date") or record.get("grant_date")

            try:
                data = (
                    normalizer.normalize_grant(record)
                    if kind == "grant"
                    else normalizer.normalize_application(record)
                )
                score, breakdown = scorer.score_dict(data)
                data["interesting_score"] = score
                data["score_breakdown"] = breakdown
                batch.append(data)
            except Exception as e:
                logger.warning(f"Normalize/score failed: {e}")
                stats["failed"] += 1
                continue

            if len(batch) >= BATCH_SIZE:
                r = await _upsert_batch_async(batch)
                stats["created"] += r["created"]
                stats["updated"] += r["updated"]
                stats["failed"] += r["failed"]
                batch = []

        # Final batch
        if batch:
            r = await _upsert_batch_async(batch)
            stats["created"] += r["created"]
            stats["updated"] += r["updated"]
            stats["failed"] += r["failed"]

        stats["files_downloaded"] += 1

        # Record source fetch — same event loop
        await _record_source_fetch_async(
            provider="odp_bulk_dataset",
            target_type=f"{kind}_week",
            target_id=file_info["fileName"],
            status="success" if stats.get("records_parsed", 0) > 0 else "empty",
            records_found=stats.get("records_parsed", 0),
            source_url=file_info.get("fileDownloadURI", ""),
        )

    stats["files_failed"] = client.stats.get("files_failed", 0)
    stats["status"] = "success" if stats["created"] > 0 or stats["updated"] > 0 else "zero_results"

    logger.info(
        f"ODP {kind} ingestion complete: {stats['created']} new, "
        f"{stats['updated']} updated, {stats['failed']} failed"
    )

    return stats


async def _upsert_batch_async(batch: list[dict]) -> dict:
    """Upsert a batch of patent records using the same async session."""
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


async def _record_source_fetch_async(
    provider: str,
    target_type: str,
    target_id: str,
    status: str,
    records_found: int = 0,
    error_message: str | None = None,
    source_url: str | None = None,
) -> None:
    """Record a source fetch attempt — same event loop."""
    from sqlalchemy import text

    async with async_session_maker() as session:
        await session.execute(
            text(
                """
                INSERT INTO source_fetches (
                    provider, office, target_type, target_id,
                    status, records_found, error_message,
                    source_url, started_at, completed_at
                ) VALUES (
                    :provider, :office, :target_type, :target_id,
                    :status, :found, :error,
                    :source_url, :started, :completed
                )
            """
            ),
            {
                "provider": provider,
                "office": "USPTO",
                "target_type": target_type,
                "target_id": target_id,
                "status": status,
                "found": records_found,
                "error": (error_message or "")[:500],
                "source_url": (source_url or "")[:1024],
                "started": datetime.now(timezone.utc),
                "completed": datetime.now(timezone.utc),
            },
        )
        await session.commit()
