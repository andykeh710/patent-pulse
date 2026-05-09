"""Celery tasks for the Phase 1 patent tagger."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.ai.tagger import tag_patent as cached_tag_patent
from app.core.exceptions import SummarizationError
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.tasks.celery_app import celery_app
from app.tasks.run_aggregates import (
    recompute_run_aggregates,
    record_run_task_completion,
    record_run_task_failure,
)

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.tag.tag_patent",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(SummarizationError,),
)
def tag_patent(self, patent_id: str, run_id: str | None = None) -> dict[str, Any]:
    """Compute tags for one patent and denormalize onto PatentPublication."""
    return asyncio.run(_tag_patent_async(patent_id, run_id))


async def _tag_patent_async(patent_id: str, run_id: str | None) -> dict[str, Any]:
    run_uuid = UUID(run_id) if run_id else None
    async with async_session_maker() as session:
        result = await session.execute(
            select(PatentPublication).where(PatentPublication.id == UUID(patent_id))
        )
        patent = result.scalar_one_or_none()
        if not patent:
            if run_uuid:
                await record_run_task_failure(session, run_uuid)
                await recompute_run_aggregates(session, run_uuid)
            return {"status": "failed", "error": "patent not found"}

        if not patent.title and not patent.abstract:
            if run_uuid:
                await record_run_task_completion(session, run_uuid)
                await recompute_run_aggregates(session, run_uuid)
            return {"status": "skipped", "reason": "no_content"}

        tags, artifact_id = await cached_tag_patent(
            session,
            patent,
            run_id=run_uuid,
        )
        patent.tags = tags
        patent.latest_tags_artifact_id = artifact_id
        await session.commit()
        if run_uuid:
            await record_run_task_completion(session, run_uuid)
            await recompute_run_aggregates(session, run_uuid)
        return {
            "status": "success",
            "artifact_id": str(artifact_id),
            "tag_count": sum(
                len(v) if isinstance(v, list) else 0 for v in tags.values()
            ),
        }


@celery_app.task(bind=True, name="app.tasks.tag.batch_tag_patents", max_retries=1)
def batch_tag_patents(self, limit: int = 50) -> dict[str, Any]:
    """Tag a batch of patents that have a summary but no tags yet."""
    return asyncio.run(_batch_tag_async(limit))


async def _batch_tag_async(limit: int) -> dict[str, Any]:
    stats = {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}
    async with async_session_maker() as session:
        stmt = (
            select(PatentPublication)
            .where(PatentPublication.summarized_at.isnot(None))
            .where(PatentPublication.tags.is_(None))
            .order_by(PatentPublication.interesting_score.desc().nullslast())
            .limit(limit)
        )
        patents = list((await session.execute(stmt)).scalars().all())

    for patent in patents:
        try:
            r = await _tag_patent_async(str(patent.id), None)
            if r["status"] == "success":
                stats["succeeded"] += 1
            elif r["status"] == "skipped":
                stats["skipped"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:  # noqa: BLE001
            stats["failed"] += 1
            logger.exception("tag failed for %s: %s", patent.id, e)
        stats["processed"] += 1
    return stats
