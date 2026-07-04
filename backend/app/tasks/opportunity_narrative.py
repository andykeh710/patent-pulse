"""Celery tasks for the Opportunity Narrative generator."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.ai.opportunity_narrative import (
    generate_opportunity_narrative as cached_generate_opportunity_narrative,
)
from app.core.exceptions import SummarizationError
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.tasks.celery_app import celery_app
from app.tasks.run_aggregates import recompute_run_aggregates

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_narrative.generate_opportunity_narrative",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(SummarizationError,),
)
def generate_opportunity_narrative(
    self, patent_id: str, run_id: str | None = None
) -> dict[str, Any]:
    """Generate Opportunity Narrative for one patent and persist artifact."""
    return asyncio.run(_generate_opportunity_narrative_async(patent_id, run_id))


async def _generate_opportunity_narrative_async(
    patent_id: str, run_id: str | None
) -> dict[str, Any]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(PatentPublication).where(PatentPublication.id == UUID(patent_id))
        )
        patent = result.scalar_one_or_none()
        if not patent:
            return {"status": "failed", "error": "patent not found"}

        if not patent.title and not patent.abstract:
            return {"status": "skipped", "reason": "no_content"}

        data, artifact_id = await cached_generate_opportunity_narrative(
            session,
            patent,
            run_id=UUID(run_id) if run_id else None,
        )
        if run_id:
            await recompute_run_aggregates(session, run_id)
        return {
            "status": "success",
            "artifact_id": str(artifact_id),
            "opportunity_type": data.get("opportunity_type", ""),
        }


@celery_app.task(
    bind=True, name="app.tasks.opportunity_narrative.batch_opportunity_narrative", max_retries=1
)
def batch_opportunity_narrative(self, limit: int = 50) -> dict[str, Any]:
    """Generate Opportunity Narrative for patents that have tags but no narrative yet."""
    return asyncio.run(_batch_opportunity_narrative_async(limit))


async def _batch_opportunity_narrative_async(limit: int) -> dict[str, Any]:
    stats = {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}
    async with async_session_maker() as session:
        # Select patents with tags and score, ordered by opportunity score descending
        stmt = (
            select(PatentPublication)
            .where(PatentPublication.tags.isnot(None))
            .where(PatentPublication.opportunity_score.isnot(None))
            .order_by(PatentPublication.opportunity_score.desc().nullslast())
            .limit(limit)
        )
        patents = list((await session.execute(stmt)).scalars().all())

    for patent in patents:
        try:
            r = await _generate_opportunity_narrative_async(str(patent.id), None)
            if r["status"] == "success":
                stats["succeeded"] += 1
            elif r["status"] == "skipped":
                stats["skipped"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:  # noqa: BLE001
            stats["failed"] += 1
            logger.exception("Opportunity Narrative failed for %s: %s", patent.id, e)
        stats["processed"] += 1
    return stats
