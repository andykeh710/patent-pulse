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

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import AIArtifact, AIRun

logger = logging.getLogger(__name__)


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
                AIArtifact.patent_publication_id,
                AIArtifact.input_hash,
                AIArtifact.input_tokens,
                AIArtifact.output_tokens,
                AIArtifact.actual_cost_usd,
            ).where(AIArtifact.run_id == run_id)
        )
    ).all()

    cached = max(int(run.cached_count or 0), 0)
    complete_keys = set()
    failed_keys = set()
    in_tokens = 0
    out_tokens = 0
    cost = 0.0
    for status, patent_id, input_hash, itok, otok, c in rows:
        item_key = str(patent_id) if patent_id else input_hash
        if status == "complete":
            complete_keys.add(item_key)
        elif status == "failed":
            failed_keys.add(item_key)
        in_tokens += int(itok or 0)
        out_tokens += int(otok or 0)
        cost += float(c or 0.0)

    completed = cached + len(complete_keys)
    failed = len(failed_keys - complete_keys)
    finished = completed + failed >= max(run.cohort_size, 1)
    new_status = run.status
    finished_at = run.finished_at
    if finished:
        new_status = "succeeded" if completed > 0 else "failed"
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


async def record_run_item_failed(
    session: AsyncSession,
    *,
    run_id: UUID | str,
    artifact_type: str,
    model: str,
    prompt_name: str,
    prompt_version: int,
    prompt_hash: str,
    input_hash: str,
    error_message: str,
    patent_publication_id: UUID | None = None,
    subject_key: str | None = None,
) -> None:
    """Record an idempotent failed AIArtifact, then recompute the parent run."""
    if isinstance(run_id, str):
        run_id = UUID(run_id)

    existing = (
        await session.execute(
            select(AIArtifact.id)
            .where(AIArtifact.run_id == run_id)
            .where(AIArtifact.artifact_type == artifact_type)
            .where(AIArtifact.input_hash == input_hash)
            .where(AIArtifact.status == "failed")
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            AIArtifact(
                patent_publication_id=patent_publication_id,
                run_id=run_id,
                artifact_type=artifact_type,
                artifact_version=1,
                model=model,
                prompt_name=prompt_name,
                prompt_version=prompt_version,
                prompt_hash=prompt_hash,
                input_hash=input_hash,
                subject_key=subject_key,
                content_json=None,
                content_text=None,
                input_tokens=0,
                output_tokens=0,
                estimated_cost_usd=0.0,
                actual_cost_usd=0.0,
                status="failed",
                error_message=error_message,
            )
        )
        await session.flush()

    await recompute_run_aggregates(session, run_id)
