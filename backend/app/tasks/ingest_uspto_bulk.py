"""
Celery tasks for USPTO official bulk data ingestion.

Uses weekly grant/application XML from USPTO as the authoritative source.
Records every source attempt in source_fetches for observability.
"""

import asyncio
from datetime import date, datetime, timedelta, timezone

from celery.utils.log import get_task_logger

from app.ai.scorer import PatentScorer
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
    """Ingest USPTO patent grants for a specific Tuesday issue date."""
    return _ingest_week("grant", date.fromisoformat(issue_date))


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_uspto_bulk.ingest_application_week",
    max_retries=1,
)
def ingest_application_week(self, publication_date: str) -> dict:
    """Ingest USPTO published applications for a specific Thursday date."""
    return _ingest_week("application", date.fromisoformat(publication_date))


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_uspto_bulk.catch_up_weeks",
    max_retries=1,
)
def catch_up_weeks(self, start_date: str = "2026-05-29", end_date: str | None = None) -> dict:
    """Ingest all USPTO grant and application weeks in a date range."""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date) if end_date else date.today()

    grants_dates = _weekdays_in_range(start, end, 1)
    apps_dates = _weekdays_in_range(start, end, 3)

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

    total["status"] = _overall_status(total)
    return total


# ── Internal ────────────────────────────────────────────────────────────


def _ingest_week(kind: str, target_date: date) -> dict:
    """
    Ingest one week of grants or applications via the ODP datasets API.

    Records every source attempt in source_fetches. Returns honest status.
    """
    from app.ingestion.uspto_odp_bulk import USPTOBulkDatasetClient

    client = USPTOBulkDatasetClient()
    normalizer = USPTONormalizer()
    scorer = PatentScorer()

    stats = {"fetched": 0, "created": 0, "updated": 0, "failed": 0, "source_status": "ok", "sources": {}}

    # Try ODP datasets API
    sources = _try_all_sources(None, kind, target_date)  # type: ignore[arg-type]
    stats["sources"] = sources

    any(s["status"] == "success" for s in sources.values())
    any_data = any(s.get("records_found", 0) > 0 for s in sources.values())

    if not any_data:
        stats["source_status"] = "empty"
        asyncio.run(_record_source_fetches(kind, target_date, sources, stats))
        return stats

    # Download and parse via ODP datasets client
    try:
        if kind == "grant":
            files = client.get_grant_files(target_date, target_date)
        else:
            files = client.get_application_files(target_date, target_date)

        normalize_fn = (
            normalizer.normalize_grant if kind == "grant" else normalizer.normalize_application
        )

        for file_info in files:
            for raw in client.download_and_parse(file_info):
                stats["fetched"] += 1
                try:
                    data = normalize_fn(raw)
                    score, breakdown = scorer.score_dict(data)
                    data["interesting_score"] = score
                    data["score_breakdown"] = breakdown
                    batch = [data]
                    r = asyncio.run(_upsert_batch(batch))
                    stats["created"] += r["created"]
                    stats["updated"] += r["updated"]
                    stats["failed"] += r["failed"]
                    if r["created"] > 0:
                        # Schedule figure fetch for newly created patents
                        from app.tasks.backfill_figures import fetch_patent_figures

                        fetch_patent_figures.delay(batch[0]["publication_number"])
                except Exception as exc:
                    stats["failed"] += 1
                    logger.warning(f"Failed to process record: {exc}")
    except Exception as exc:
        logger.error(f"{kind} ingestion failed: {exc}", exc_info=True)
        stats["error"] = str(exc)[:500]
        stats["source_status"] = "failed"

    # ── Record source_fetches rows ──
    asyncio.run(_record_source_fetches(kind, target_date, sources, stats))

    logger.info(
        f"{kind} week {target_date}: {stats['source_status']} "
        f"({stats['created']} new, {stats['fetched']} fetched)"
    )
    return stats


def _try_all_sources(client: USPTOBulkClient, kind: str, target_date: date) -> dict:
    """
    Attempt to fetch from the new USPTO ODP datasets API.
    The legacy bulkdata.uspto.gov and developer.uspto.gov endpoints were
    retired June 2026. We now use api.uspto.gov/api/v1/datasets/products/.
    """
    from app.ingestion.uspto_odp_bulk import USPTOBulkDatasetClient

    results = {}

    # Source: ODP datasets API (api.uspto.gov)
    odp_client = USPTOBulkDatasetClient()
    product_id = "PTGRXML" if kind == "grant" else "APPXML"
    odp_result = {
        "provider": "uspto_odp",
        "source_url": f"{odp_client.base}/datasets/products/{product_id}",
        "status": "unavailable",
        "http_status": None,
        "records_found": 0,
        "error_message": None,
    }
    try:
        files = (
            odp_client.get_grant_files(target_date, target_date)
            if kind == "grant"
            else odp_client.get_application_files(target_date, target_date)
        )
        if files:
            total_size = sum(f.get("fileSize", 0) for f in files)
            odp_result["status"] = "success"
            odp_result["records_found"] = total_size
        else:
            odp_result["status"] = "empty"
    except Exception as e:
        odp_result["status"] = "unavailable"
        odp_result["error_message"] = str(e)[:500]
    results["uspto_odp"] = odp_result

    return results


async def _record_source_fetches(
    kind: str,
    target_date: date,
    sources: dict,
    stats: dict,
) -> None:
    """Write source_fetches rows for every attempted source."""
    from sqlalchemy import text

    now = datetime.now(timezone.utc)
    async with async_session_maker() as session:
        for provider, source in sources.items():
            await session.execute(
                text("""
                INSERT INTO source_fetches (
                    provider, office, target_type, target_id,
                    status, http_status, records_found,
                    error_message, source_url, started_at, completed_at
                ) VALUES (
                    :provider, :office, :target_type, :target_id,
                    :status, :http_status, :found,
                    :error, :source_url, :started, :completed
                )
            """),
                {
                    "provider": provider,
                    "office": "USPTO",
                    "target_type": f"{kind}_week",
                    "target_id": target_date.isoformat(),
                    "status": source["status"],
                    "http_status": source.get("http_status"),
                    "found": source.get("records_found", 0),
                    "error": (source.get("error_message") or "")[:500],
                    "source_url": (source.get("source_url") or "")[:1024],
                    "started": now,
                    "completed": now,
                },
            )
        await session.commit()


async def _upsert_batch(batch: list[dict]) -> dict:
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


def _overall_status(total: dict) -> str:
    """Determine overall catch-up status."""
    if total["created"] > 0 or total["updated"] > 0:
        return "success" if total["failed"] == 0 else "partial_success"
    return "unavailable"


def _weekdays_in_range(start: date, end: date, weekday: int) -> list[date]:
    result = []
    current = start
    while current <= end:
        if current.weekday() == weekday:
            result.append(current)
        current += timedelta(days=1)
    return result
