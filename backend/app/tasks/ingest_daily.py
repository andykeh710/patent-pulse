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
import logging
from datetime import date, datetime, timedelta, timezone

from celery.utils.log import get_task_logger

from app.config import settings
from app.core.exceptions import TransientIngestionError
from app.database import async_session_maker
from app.tasks.celery_app import celery_app
from app.tasks.ingest_applications import ingest_applications_range
from app.tasks.ingest_grants import ingest_grants_range

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
        result = await session.execute(
            select(func.max(PatentPublication.publication_date))
        )
        return result.scalar()


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
    # Temporarily override the lookback for this run
    original = settings.ingest_lookback_days
    settings.ingest_lookback_days = lookback_days
    try:
        return run_daily_ingestion()
    finally:
        settings.ingest_lookback_days = original


@celery_app.task(
    bind=True,
    name="app.tasks.ingest_daily.run_daily_ingestion",
    max_retries=1,
    default_retry_delay=600,
)
def run_daily_ingestion(self) -> dict:
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
        lookback_days = asyncio.run(_compute_lookback_days())
        start_date = end_date - timedelta(days=lookback_days)

        logger.info(f"Daily ingestion: {start_date} → {end_date} (lookback={lookback_days}d)")

        # Phase 1: Fetch grants
        grants_stats = {}
        try:
            grants_task = ingest_grants_range.delay(
                start_date.isoformat(), end_date.isoformat()
            )
            grants_stats = grants_task.get(timeout=1800)  # 30 min timeout
            logger.info(f"Grants: {grants_stats}")
        except Exception as e:
            logger.error(f"Grant ingestion failed: {e}")
            grants_stats = {"processed": 0, "created": 0, "updated": 0, "failed": 1}

        # Phase 2: Fetch applications
        apps_stats = {}
        try:
            apps_task = ingest_applications_range.delay(
                start_date.isoformat(), end_date.isoformat()
            )
            apps_stats = apps_task.get(timeout=1800)
            logger.info(f"Applications: {apps_stats}")
        except Exception as e:
            logger.error(f"Application ingestion failed: {e}")
            apps_stats = {"processed": 0, "created": 0, "updated": 0, "failed": 1}

        total_new = grants_stats.get("created", 0) + apps_stats.get("created", 0)
        total_updated = grants_stats.get("updated", 0) + apps_stats.get("updated", 0)
        total_failed = grants_stats.get("failed", 0) + apps_stats.get("failed", 0)

        asyncio.run(
            _record_ingestion_run(
                status="success",
                grants_stats=grants_stats,
                apps_stats=apps_stats,
                started_at=started_at,
            )
        )

        # Phase 3: Trigger downstream refresh if new records were ingested
        if total_new > 0:
            _trigger_downstream_refresh(total_new)

        stats.update(
            {
                "status": "success",
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
        asyncio.run(
            _record_ingestion_run(
                status="failed", error=str(e), started_at=started_at
            )
        )
        stats["status"] = "failed"
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

    batch_score_opportunity.apply_async(
        kwargs={"limit": 500}, queue="summarization"
    )

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
