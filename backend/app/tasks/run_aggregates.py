"""Helpers to recompute AIRun aggregates from AIArtifact ground truth.

Per-patent worker tasks (tag_patent, score_patent_opportunity_task, ...) are
fan-out workers; the parent ``AIRun`` row needs its ``completed_count``,
``failed_count``, ``actual_cost_usd``, ``actual_input_tokens`` and
``status`` / ``finished_at`` updated as artifacts land.

Rather than have each worker increment counters (which races) we recompute
the aggregate from the ``ai_artifacts`` table on every call. This is
idempotent, race-free, and resilient to lost messages -- if a task is
re-run, the aggregate self-corrects.
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import AIArtifact, AIRun

logger = logging.getLogger(__name__)


async def record_run_task_completion(
    session: AsyncSession, run_id: UUID | str
) -> None:
    """Record that one dispatched task reached a terminal non-failed outcome."""
    if isinstance(run_id, str):
        run_id = UUID(run_id)

    await session.execute(
        update(AIRun)
        .where(AIRun.id == run_id)
        .where(AIRun.status.notin_(("succeeded", "failed", "cancelled")))
        .values(completed_count=AIRun.completed_count + 1)
    )


async def record_run_task_failure(session: AsyncSession, run_id: UUID | str) -> None:
    """Record that one dispatched task reached a terminal failed outcome."""
    if isinstance(run_id, str):
        run_id = UUID(run_id)

    await session.execute(
        update(AIRun)
        .where(AIRun.id == run_id)
        .where(AIRun.status.notin_(("succeeded", "failed", "cancelled")))
        .values(failed_count=AIRun.failed_count + 1)
    )


async def recompute_run_aggregates(
    session: AsyncSession, run_id: UUID | str
) -> None:
    """Recompute counters + finalize status for one AIRun.

    Safe to call after every per-patent task completion. Will:
      - SUM artifact counts grouped by status into completed/failed
      - SUM tokens + cost
      - Mark the run ``succeeded`` (or ``failed`` if every artifact failed)
        once ``completed + failed >= cohort_size``, setting ``finished_at``.

    Does nothing if the run is already in a terminal state.
    """
    if isinstance(run_id, str):
        run_id = UUID(run_id)

    run = (
        await session.execute(select(AIRun).where(AIRun.id == run_id))
    ).scalar_one_or_none()
    if run is None:
        logger.warning("recompute_run_aggregates: run %s not found", run_id)
        return
    if run.status in ("succeeded", "failed", "cancelled"):
        return

    rows = (
        await session.execute(
            select(
                AIArtifact.status,
                func.count(AIArtifact.id),
                func.coalesce(func.sum(AIArtifact.input_tokens), 0),
                func.coalesce(func.sum(AIArtifact.output_tokens), 0),
                func.coalesce(func.sum(AIArtifact.actual_cost_usd), 0.0),
            )
            .where(AIArtifact.run_id == run_id)
            .group_by(AIArtifact.status)
        )
    ).all()

    completed = 0
    failed = 0
    in_tokens = 0
    out_tokens = 0
    cost = 0.0
    for status, count, itok, otok, c in rows:
        if status == "complete":
            completed += int(count)
        elif status == "failed":
            failed += int(count)
        in_tokens += int(itok or 0)
        out_tokens += int(otok or 0)
        cost += float(c or 0.0)

    completed = max(completed, int(getattr(run, "completed_count", 0) or 0))
    failed = max(failed, int(getattr(run, "failed_count", 0) or 0))
    cohort_size = max(int(run.cohort_size or 0), 0)
    finished = completed + failed >= cohort_size
    new_status = run.status
    finished_at = run.finished_at
    if finished:
        new_status = "succeeded" if completed > 0 or cohort_size == 0 else "failed"
        finished_at = finished_at or datetime.utcnow()

    await session.execute(
        update(AIRun)
        .where(AIRun.id == run_id)
        .values(
            completed_count=completed,
            failed_count=failed,
            actual_input_tokens=in_tokens,
            actual_output_tokens=out_tokens,
            actual_cost_usd=cost,
            status=new_status,
            finished_at=finished_at,
        )
    )
    await session.commit()
