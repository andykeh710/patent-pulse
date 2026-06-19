"""
Celery tasks for USPTO official bulk data ingestion.

Uses weekly grant/application XML from USPTO as the authoritative source.
Records every source attempt in source_fetches for observability.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

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
    Ingest one week of grants or applications.

    Records every source attempt in source_fetches. Returns honest status.
    """
    client = USPTOBulkClient()
    normalizer = USPTONormalizer()
    scorer = PatentScorer()

    stats = {"fetched": 0, "created": 0, "updated": 0, "failed": 0, "sources": {}}

    # Try each source
    sources = _try_all_sources(client, kind, target_date)
    stats["sources"] = sources

    # Determine status
    any_success = any(s["status"] == "success" for s in sources.values())
    any_fetched = any(s.get("records_found", 0) > 0 for s in sources.values())
    all_down = all(s["status"] in ("failed", "unavailable") for s in sources.values())

    if any_fetched:
        stats["source_status"] = "success" if not any(
            s["status"] == "unavailable" for s in sources.values()
        ) else "partial_success"
    elif all_down:
        stats["source_status"] = "unavailable"
    else:
        stats["source_status"] = "empty"

    # If we got data, process it
    if any_fetched:
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
            logger.error(f"{kind} ingestion failed: {exc}", exc_info=True)
            stats["error"] = str(exc)[:500]

    # ── Record source_fetches rows ──
    asyncio.run(_record_source_fetches(kind, target_date, sources, stats))

    logger.info(f"{kind} week {target_date}: {stats['source_status']} "
                f"({stats['created']} new, {stats['fetched']} fetched)")
    return stats


def _try_all_sources(client: USPTOBulkClient, kind: str, target_date: date) -> dict:
    """
    Attempt to fetch from each configured source and return per-source results.

    Does NOT do full XML parsing — just checks reachability and data presence.
    """
    results = {}

    # Source 1: bulkdata.uspto.gov (ZIP download)
    year = target_date.year
    date_str = target_date.strftime("%m%d%Y")
    if kind == "grant":
        bulk_url = f"https://bulkdata.uspto.gov/data/patent/grant/redbook/full/{year}/ipg{date_str}.zip"
    else:
        bulk_url = f"https://bulkdata.uspto.gov/data/patent/application/redbook/full/{year}/ipa{date_str}.zip"

    bulk_result = {
        "provider": "uspto_bulkdata",
        "source_url": bulk_url,
        "status": "unavailable",
        "http_status": None,
        "records_found": 0,
        "error_message": None,
    }
    try:
        import httpx
        r = httpx.head(bulk_url, timeout=15, follow_redirects=True)
        bulk_result["http_status"] = r.status_code
        if r.status_code == 200:
            content_len = int(r.headers.get("content-length", 0))
            bulk_result["status"] = "success" if content_len > 100 else "empty"
            bulk_result["records_found"] = content_len
        else:
            bulk_result["status"] = "unavailable"
            bulk_result["error_message"] = f"HTTP {r.status_code}"
    except Exception as e:
        bulk_result["status"] = "unavailable"
        bulk_result["error_message"] = f"DNS/network failure: {e}"
    results["uspto_bulkdata"] = bulk_result

    # Source 2: ODP IBD API
    odp_url = f"{client.base_url}/patent/{kind}s"
    odp_result = {
        "provider": "uspto_odp",
        "source_url": odp_url,
        "status": "unavailable",
        "http_status": None,
        "records_found": 0,
        "error_message": None,
    }
    try:
        import httpx
        params = {"dateFrom": target_date.isoformat(), "dateTo": target_date.isoformat()}
        if client.api_key:
            params["api_key"] = client.api_key
        r = httpx.get(odp_url, params=params, timeout=30)
        odp_result["http_status"] = r.status_code
        if r.status_code == 200:
            content_len = len(r.content)
            odp_result["status"] = "success" if content_len > 100 else "empty"
            odp_result["records_found"] = content_len
        else:
            odp_result["status"] = "unavailable"
            odp_result["error_message"] = f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        odp_result["status"] = "source_unavailable"
        odp_result["error_message"] = f"Connection failure: {e}"
    results["uspto_odp"] = odp_result

    return results


async def _record_source_fetches(
    kind: str, target_date: date, sources: dict, stats: dict,
) -> None:
    """Write source_fetches rows for every attempted source."""
    from sqlalchemy import text

    now = datetime.now(timezone.utc)
    async with async_session_maker() as session:
        for provider, source in sources.items():
            await session.execute(text("""
                INSERT INTO source_fetches (
                    provider, office, target_type, target_id,
                    status, http_status, records_found,
                    error_message, source_url, started_at, completed_at
                ) VALUES (
                    :provider, :office, :target_type, :target_id,
                    :status, :http_status, :found,
                    :error, :source_url, :started, :completed
                )
            """), {
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
            })
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
