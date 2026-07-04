"""
Assignee normalization backfill task.

Populates the ``assignees`` table from the ``assignees`` JSONB column on
``patent_publications``, using the ``normalize_assignee()`` PostgreSQL
function for grouping. Idempotent — re-running is safe and updates
``patent_count`` for existing rows.

Scheduled by Celery beat once daily at 04:00 UTC to keep assignees in
sync with newly ingested patents.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from app.database import async_session_maker
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Backfill SQL

BACKFILL_SQL = """
INSERT INTO assignees (id, normalized_name, display_name, aliases, patent_count, created_at, updated_at)
SELECT
    gen_random_uuid(),
    nrm.name AS normalized_name,
    nrm.display_name,
    jsonb_build_array(nrm.display_name),
    nrm.patent_count,
    now(),
    now()
FROM (
    SELECT
        normalize_assignee(av.val) AS name,
        -- Pick the longest raw name as the display form.
        (array_agg(av.val ORDER BY length(av.val) DESC))[1] AS display_name,
        COUNT(DISTINCT p.id) AS patent_count
    FROM patent_publications p
    JOIN LATERAL jsonb_array_elements_text(p.assignees) AS av(val) ON true
    WHERE av.val IS NOT NULL AND av.val != ''
    GROUP BY normalize_assignee(av.val)
) nrm
ON CONFLICT (normalized_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    patent_count = EXCLUDED.patent_count,
    updated_at = now()
-- NOTE: entity_type and country are intentionally NOT set by this backfill.
-- entity_type enrichment requires an external data source (USPTO PatentsView,
-- EPO Open Patent Services, or similar) with provenance tracking.
-- Country enrichment likewise requires authoritative source data.
-- See docs/v3-v4-roadmap.md § V3.5 for the enrichment plan.
"""


async def backfill_assignees() -> dict[str, Any]:
    """Backfill (or refresh) the assignees table.

    Returns a summary dict with keys: total_processed, inserted, updated.
    Idempotent — the ON CONFLICT clause handles existing rows.
    """
    stats: dict[str, int] = {"total_processed": 0, "inserted": 0, "updated": 0}

    async with async_session_maker() as session:
        # Count rows before
        before = await session.execute(text("SELECT COUNT(*) FROM assignees"))
        before_count = before.scalar() or 0

        # Run the upsert
        await session.execute(text(BACKFILL_SQL))
        await session.commit()

        # Count rows after
        after = await session.execute(text("SELECT COUNT(*) FROM assignees"))
        after_count = after.scalar() or 0

        stats["total_processed"] = after_count
        stats["inserted"] = max(0, after_count - before_count)
        stats["updated"] = after_count  # every row touched by the upsert

        logger.info(
            "Assignee backfill: total=%d inserted=%d updated=%d",
            stats["total_processed"],
            stats["inserted"],
            stats["updated"],
        )
        return stats


async def backfill_assignees_for_session(
    session,
) -> dict[str, Any]:
    """Session-aware variant for testing.

    Accepts a pre-existing SQLAlchemy AsyncSession so tests can seed
    patent data and verify the backfill in the same transaction.
    """
    stats: dict[str, int] = {"total_processed": 0, "inserted": 0, "updated": 0}

    before = await session.execute(text("SELECT COUNT(*) FROM assignees"))
    before_count = before.scalar() or 0

    await session.execute(text(BACKFILL_SQL))
    await session.commit()

    after = await session.execute(text("SELECT COUNT(*) FROM assignees"))
    after_count = after.scalar() or 0

    stats["total_processed"] = after_count
    stats["inserted"] = max(0, after_count - before_count)
    stats["updated"] = after_count

    return stats


# ---------------------------------------------------------------------------
# Celery task (for beat scheduling)
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="app.tasks.backfill_assignees.backfill_assignees_task",
    max_retries=1,
)
def backfill_assignees_task(self) -> dict[str, Any]:
    """Celery task — runs the async backfill in a fresh event loop.

    Beat schedule invokes this daily at 04:00 UTC. Idempotent via
    ON CONFLICT (normalized_name) DO UPDATE.
    """
    import asyncio

    async def _run() -> dict[str, Any]:
        return await backfill_assignees()

    return asyncio.run(_run())
