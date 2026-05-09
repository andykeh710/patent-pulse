"""Celery tasks for the rules-based opportunity scorer."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.ai.opportunity_scorer import (
    RULES_VERSION,
    score_patent_opportunity,
)
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.tasks.celery_app import celery_app
from app.tasks.run_aggregates import (
    recompute_run_aggregates,
    record_run_task_completion,
)

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity.score_patent_opportunity",
    max_retries=2,
    default_retry_delay=30,
)
def score_patent_opportunity_task(
    self, patent_id: str, run_id: str | None = None
) -> dict[str, Any]:
    """Compute opportunity_score for one patent + denormalize."""
    return asyncio.run(_score_async(patent_id, run_id))


async def _score_async(patent_id: str, run_id: str | None) -> dict[str, Any]:
    async with async_session_maker() as session:
        patent = (
            await session.execute(
                select(PatentPublication).where(
                    PatentPublication.id == UUID(patent_id)
                )
            )
        ).scalar_one_or_none()
        if not patent:
            return {"status": "failed", "error": "patent not found"}

        breakdown, artifact_id = await score_patent_opportunity(
            session,
            patent,
            run_id=UUID(run_id) if run_id else None,
        )
        patent.opportunity_score = float(breakdown["score"])
        patent.opportunity_score_version = int(breakdown["version"])
        patent.opportunity_breakdown = breakdown
        await session.commit()
        if run_id:
            await record_run_task_completion(session, run_id)
            await recompute_run_aggregates(session, run_id)
        return {
            "status": "success",
            "artifact_id": str(artifact_id),
            "score": breakdown["score"],
            "version": breakdown["version"],
        }


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity.batch_score_opportunity",
    max_retries=1,
)
def batch_score_opportunity(self, limit: int = 200) -> dict[str, Any]:
    """Score a batch of patents whose opportunity_score is null or stale."""
    return asyncio.run(_batch_score_async(limit))


async def _batch_score_async(limit: int) -> dict[str, Any]:
    stats = {"processed": 0, "succeeded": 0, "failed": 0}
    async with async_session_maker() as session:
        stmt = (
            select(PatentPublication)
            .where(
                (PatentPublication.opportunity_score.is_(None))
                | (PatentPublication.opportunity_score_version != RULES_VERSION)
            )
            .order_by(PatentPublication.estimated_expiry_date.asc().nullslast())
            .limit(limit)
        )
        patents = list((await session.execute(stmt)).scalars().all())

    for p in patents:
        try:
            r = await _score_async(str(p.id), None)
            if r["status"] == "success":
                stats["succeeded"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:  # noqa: BLE001
            stats["failed"] += 1
            logger.exception("score failed for %s: %s", p.id, e)
        stats["processed"] += 1
    return stats
