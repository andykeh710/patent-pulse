"""Celery tasks for Assignee Intelligence."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.ai.assignee_intelligence import generate_assignee_intelligence
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.tasks.celery_app import celery_app
from app.tasks.run_aggregates import (
    recompute_run_aggregates,
    record_run_task_completion,
    record_run_task_failure,
)

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.assignee_intelligence.generate_assignee_intelligence", max_retries=2, default_retry_delay=30)
def generate_assignee_intelligence_task(self, patent_id: str, run_id: str | None = None) -> dict[str, Any]:
    return asyncio.run(_gen_async(patent_id, run_id))


async def _gen_async(patent_id: str, run_id: str | None) -> dict[str, Any]:
    run_uuid = UUID(run_id) if run_id else None
    async with async_session_maker() as session:
        patent = (await session.execute(select(PatentPublication).where(PatentPublication.id == UUID(patent_id)))).scalar_one_or_none()
        if not patent:
            if run_uuid:
                await record_run_task_failure(session, run_uuid)
                await recompute_run_aggregates(session, run_uuid)
            return {"status": "failed", "error": "patent not found"}
        intel, artifact_id = await generate_assignee_intelligence(session, patent, run_id=run_uuid)
        await session.commit()
        if run_uuid:
            await record_run_task_completion(session, run_uuid)
            await recompute_run_aggregates(session, run_uuid)
        return {"status": "success", "artifact_id": str(artifact_id), "assignee_intelligence_score": intel.get("assignee_intelligence_score")}


@celery_app.task(bind=True, name="app.tasks.assignee_intelligence.batch_assignee_intelligence", max_retries=1)
def batch_assignee_intelligence(self, limit: int = 200) -> dict[str, Any]:
    return asyncio.run(_batch_async(limit))


async def _batch_async(limit: int) -> dict[str, Any]:
    stats = {"processed": 0, "succeeded": 0, "failed": 0}
    async with async_session_maker() as session:
        stmt = select(PatentPublication).where(PatentPublication.opportunity_score.isnot(None)).order_by(PatentPublication.opportunity_score.desc().nullslast()).limit(limit)
        patents = list((await session.execute(stmt)).scalars().all())
    for p in patents:
        try:
            r = await _gen_async(str(p.id), None)
            if r["status"] == "success":
                stats["succeeded"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:
            stats["failed"] += 1
            logger.exception("assignee_intelligence failed for %s: %s", p.id, e)
        stats["processed"] += 1
    return stats
