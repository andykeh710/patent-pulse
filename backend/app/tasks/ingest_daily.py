"""
Daily incremental USPTO ingestion with freshness tracking.

Replaces the weekly-only schedule with a nightly catch-up:
- Runs daily at 2am
- Pulls the last 7 days of USPTO grants + applications (idempotent via doc_id upsert)
- Records ingestion runs with timing and result metadata
- Triggers downstream refresh chain on new records
- Uses a Redis lock to prevent overlapping runs
"""

import asyncio
from datetime import date, datetime, timedelta, timezone

from celery.utils.log import get_task_logger

from app.config import settings
from app.database import async_session_maker
from app.tasks.celery_app import celery_app
from app.tasks.ingest_bigquery import ingest_from_bigquery_range
from app.tasks.ingest_uspto_bulk import catch_up_weeks

logger = get_task_logger(__name__)

# Redis lock key — prevents overlapping ingestion runs
LOCK_KEY = "ingestion:daily:lock"
LOCK_TTL = 7200  # 2 hours — more than enough for a daily run


def _acquire_lock() -> bool:
    """Acquire a Redis-backed lock to prevent overlapping runs. Returns True if acquired."""
    import redis

    r = redis.from_url(settings.redis_url)
    acquired = bool(r.set(LOCK_KEY, "1", nx=True, ex=LOCK_TTL))
    if not acquired:
        logger.warning("Daily ingestion skipped — lock held by another worker")
    return acquired


def _release_lock() -> None:
    """Release the ingestion lock."""
    import redis

    r = redis.from_url(settings.redis_url)
    r.delete(LOCK_KEY)


async def _record_ingestion_run(
    status: str,
    grants_stats: dict | None = None,
    apps_stats: dict | None = None,
    error: str | None = None,
    started_at: datetime | None = None,
) -> None:
    """Record an ingestion run in the database."""
    from sqlalchemy import text

    finished_at = datetime.now(timezone.utc)
    async with async_session_maker() as session:
        await session.execute(
            text("""
                INSERT INTO ingestion_runs (
                    status, started_at, finished_at,
                    grants_processed, grants_created, grants_updated, grants_failed,
                    apps_processed, apps_created, apps_updated, apps_failed,
                    error_message
                ) VALUES (
                    :status, :started_at, :finished_at,
                    :g_proc, :g_created, :g_updated, :g_failed,
                    :a_proc, :a_created, :a_updated, :a_failed,
                    :error
                )
            """),
            {
                "status": status,
                "started_at": started_at or datetime.now(timezone.utc),
                "finished_at": finished_at,
                "g_proc": grants_stats.get("processed", 0) if grants_stats else 0,
                "g_created": grants_stats.get("created", 0) if grants_stats else 0,
                "g_updated": grants_stats.get("updated", 0) if grants_stats else 0,
                "g_failed": grants_stats.get("failed", 0) if grants_stats else 0,
                "a_proc": apps_stats.get("processed", 0) if apps_stats else 0,
                "a_created": apps_stats.get("created", 0) if apps_stats else 0,
                "a_updated": apps_stats.get("updated", 0) if apps_stats else 0,
                "a_failed": apps_stats.get("failed", 0) if apps_stats else 0,
                "error": error,
            },
        )
        await session.commit()


async def _get_latest_publication_date() -> date | None:
    """Get the most recent publication_date in the database."""
    from sqlalchemy import func, select

    from app.core.models import PatentPublication

    async with async_session_maker() as session:
        result = await session.execute(select(func.max(PatentPublication.publication_date)))
        return result.scalar()


async def _record_source_fetch(
    provider: str,
    office: str,
    target_type: str,
    target_id: str,
    stats: dict,
    error: str | None,
) -> None:
    """Record a per-source fetch attempt in source_fetches."""
    from sqlalchemy import text

    async with async_session_maker() as session:
        await session.execute(
            text("""
            INSERT INTO source_fetches (
                provider, office, target_type, target_id,
                status, records_found, error_message,
                started_at, completed_at, duration_ms
            ) VALUES (
                :provider, :office, :target_type, :target_id,
                :status, :found, :error,
                now(), now(), :ms
            )
        """),
            {
                "provider": provider,
                "office": office,
                "target_type": target_type,
                "target_id": target_id,
                "status": "success"
                if (not error and stats.get("fetched", 0) > 0)
                else ("failed" if error else "empty"),
                "found": stats.get("fetched", 0) or stats.get("processed", 0),
                "error": error[:500] if error else None,
                "ms": 0,
            },
        )
        await session.commit()


async def _compute_lookback_days() -> int:
    """
    Compute how many days back to look for new patents.

    Normal operation: uses INGEST_LOOKBACK_DAYS (default 7).
    Catch-up mode: if the last successful ingestion was more than
    INGEST_LOOKBACK_DAYS ago, expands to cover the gap (capped at 30 days).
    First run (no ingestion history): uses 30 days.
    """
    from datetime import date

    from sqlalchemy import text

    max_lookback = getattr(settings, "ingest_max_lookback_days", 30)
    default_lookback = settings.ingest_lookback_days

    async with async_session_maker() as session:
        result = await session.execute(
            text("""
                SELECT finished_at
                FROM ingestion_runs
                WHERE status = 'success'
                ORDER BY finished_at DESC
                LIMIT 1
            """)
        )
        row = result.first()

    if not row or not row.finished_at:
        # Never run successfully — catch up from 30 days
        return max_lookback

    days_since = (date.today() - row.finished_at.date()).days
    if days_since > default_lookback:
        # Gap detected — expand lookback to cover it
        return min(days_since + default_lookback, max_lookback)

    return default_lookback


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_daily.run_catch_up_ingestion",
    max_retries=1,
)
def run_catch_up_ingestion(self, lookback_days: int = 30) -> dict:
    """
    One-time catch-up ingestion for manual gap recovery.

    Uses a configurable lookback (default 30 days) to fill gaps
    after extended worker downtime. Safe to run repeatedly —
    records are upserted by doc_id.

    Args:
        lookback_days: How many days back to fetch (default 30)
    """
    return run_daily_ingestion(override_lookback_days=lookback_days)


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_daily.run_daily_ingestion",
    max_retries=1,
    default_retry_delay=600,
)
def run_daily_ingestion(self, override_lookback_days: int | None = None) -> dict:
    """
    Daily incremental USPTO ingestion with automatic gap detection.

    Normal operation: fetches the last INGEST_LOOKBACK_DAYS (default 7) of
    USPTO grants and published applications.

    Catch-up mode: if the last successful ingestion was more than
    INGEST_LOOKBACK_DAYS ago, dynamically expands the lookback to cover the
    gap (capped at 30 days to avoid overwhelming the USPTO API).

    Idempotent — records are upserted by doc_id, never duplicated.
    Safe to run manually or on schedule.
    """
    if not _acquire_lock():
        return {"status": "skipped", "reason": "lock held by another worker"}

    started_at = datetime.now(timezone.utc)
    stats = {"status": "started", "started_at": started_at.isoformat()}

    try:
        end_date = date.today()
        lookback_days = override_lookback_days or asyncio.run(_compute_lookback_days())
        start_date = end_date - timedelta(days=lookback_days)

        logger.info(f"Daily ingestion: {start_date} → {end_date} (lookback={lookback_days}d)")

        # Phase 1: Check BigQuery (supplemental — not authoritative for freshness)
        bq_stats = {}
        bq_error = None
        try:
            bq_stats = ingest_from_bigquery_range(start_date, end_date)
            logger.info(f"BigQuery (supplemental): {bq_stats}")
        except Exception as e:
            logger.error(f"BigQuery check failed: {e}", exc_info=True)
            bq_error = str(e)[:500]
            bq_stats = {"processed": 0, "created": 0, "updated": 0, "failed": 1, "fetched": 0}

        # Record source fetch for BigQuery
        asyncio.run(
            _record_source_fetch(
                "bigquery",
                "US",
                "grants_range",
                f"{start_date.isoformat()}:{end_date.isoformat()}",
                bq_stats,
                bq_error,
            )
        )

        # Phase 2: USPTO ODP bulk (official weekly XML — when available)
        odp_stats = {}
        odp_error = None
        try:
            odp_stats = catch_up_weeks(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            logger.info(f"ODP bulk: {odp_stats}")
        except Exception as e:
            logger.error(f"ODP bulk ingestion failed: {e}", exc_info=True)
            odp_error = str(e)[:500]
            odp_stats = {"created": 0, "updated": 0, "failed": 1}

        asyncio.run(
            _record_source_fetch(
                "uspto_odp",
                "US",
                "bulk_weekly",
                f"{start_date.isoformat()}:{end_date.isoformat()}",
                odp_stats,
                odp_error,
            )
        )

        # Merge stats: BigQuery + ODP
        grants_stats = {
            "processed": (bq_stats.get("fetched", 0) or bq_stats.get("processed", 0))
            + (odp_stats.get("fetched", 0) or 0),
            "created": bq_stats.get("created", 0) + odp_stats.get("created", 0),
            "updated": bq_stats.get("updated", 0) + odp_stats.get("updated", 0),
            "failed": (1 if (bq_error or bq_stats.get("error")) else 0)
            + (1 if (odp_error or odp_stats.get("error")) else 0),
        }
        apps_stats = {"processed": 0, "created": 0, "updated": 0, "failed": 0}

        if not bq_error and not bq_stats.get("error"):
            total_new = bq_stats.get("created", 0) + odp_stats.get("created", 0)
            total_updated = bq_stats.get("updated", 0) + odp_stats.get("updated", 0)
            total_failed = bq_stats.get("failed", 0) + odp_stats.get("failed", 0)
            (bq_stats.get("fetched", 0) or bq_stats.get("processed", 0)) + (
                odp_stats.get("fetched", 0) or 0
            )

            if total_new > 0 or total_updated > 0:
                status = "success"
            elif (
                odp_stats.get("source_status") == "unavailable" and bq_stats.get("fetched", 0) == 0
            ):
                status = "degraded"
            else:
                status = "success"  # ran successfully, just no new data
            error_msg = None
        else:
            total_new = 0
            total_updated = 0
            total_failed = 1
            status = "degraded"
            errors = []
            if bq_error or bq_stats.get("error"):
                errors.append(f"BigQuery: {bq_error or bq_stats.get('error')}")
            error_msg = "; ".join(errors) if errors else None

        asyncio.run(
            _record_ingestion_run(
                status=status,
                grants_stats=grants_stats,
                apps_stats=apps_stats,
                started_at=started_at,
                error=error_msg,
            )
        )

        # Phase 3: Trigger downstream refresh if new records were ingested
        if total_new > 0:
            _trigger_downstream_refresh(total_new)

        stats.update(
            {
                "status": status,
                "grants": grants_stats,
                "applications": apps_stats,
                "total_new": total_new,
                "total_updated": total_updated,
                "total_failed": total_failed,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        logger.info(
            f"Daily ingestion complete: {total_new} new, {total_updated} updated, {total_failed} failed"
        )

    except Exception as e:
        logger.error(f"Daily ingestion failed: {e}", exc_info=True)
        asyncio.run(_record_ingestion_run(status="degraded", error=str(e), started_at=started_at))
        stats["status"] = "degraded"
        stats["error"] = str(e)

    finally:
        _release_lock()

    return stats


def _trigger_downstream_refresh(new_record_count: int) -> None:
    """
    After ingestion finds new records, trigger the downstream pipeline.

    Chain:
    1. Enrich abstracts (for patents without abstracts)
    2. Theme matching (re-match all themes against new records)
    3. Opportunity scoring (score unscored patents)
    4. Trend computation (recompute weekly trends)
    5. Today state refresh
    """
    logger.info(f"Triggering downstream refresh for {new_record_count} new records")

    # Enrich abstracts for new un-enriched records
    from app.tasks.enrich_abstracts import enrich_batch

    enrich_batch.apply_async(kwargs={"batch_size": 500}, queue="ingestion")

    # Re-match themes (new records may match)
    from app.tasks.theme_matcher import match_all_themes

    match_all_themes.apply_async(kwargs={"limit_per_theme": 500}, queue="maintenance")

    # Score unscored patents
    from app.tasks.opportunity import batch_score_opportunity

    batch_score_opportunity.apply_async(kwargs={"limit": 500}, queue="summarization")

    # Recompute trends
    from app.tasks.compute_trends import compute_weekly_trends

    compute_weekly_trends.apply_async(queue="maintenance")

    # Today state is computed on each request — always fresh.
    # No separate refresh task needed.


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_daily.get_latest_ingestion_status",
)
def get_latest_ingestion_status(self) -> dict:
    """Return the most recent ingestion run status for health checks."""
    import asyncio

    async def _get():
        from sqlalchemy import text

        async with async_session_maker() as session:
            result = await session.execute(
                text("""
                    SELECT status, started_at, finished_at,
                           grants_processed, grants_created, apps_processed, apps_created,
                           error_message
                    FROM ingestion_runs
                    ORDER BY started_at DESC
                    LIMIT 1
                """)
            )
            row = result.first()
            if not row:
                return {"status": "never_run"}
            return {
                "status": row.status,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
                "grants_processed": row.grants_processed,
                "grants_created": row.grants_created,
                "apps_processed": row.apps_processed,
                "apps_created": row.apps_created,
                "error": row.error_message,
            }

    return asyncio.run(_get())
