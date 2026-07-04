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
from app.tasks.run_aggregates import recompute_run_aggregates

logger = logging.getLogger(__name__)

# Track consecutive Anthropic credit errors for circuit breaking
_anthropic_error_count = 0
_LAST_ANTHROPIC_ERROR_AT: str | None = None
ANTHROPIC_ERROR_MAX_CONSECUTIVE = 3


def _is_anthropic_error(exception: Exception) -> str | None:
    """Check if exception is an Anthropic API error.

    Returns error type string ('credits_exhausted', 'rate_limited', 'auth_error')
    or None if not an Anthropic error.
    """
    msg = str(exception).lower()
    if "credit balance is too low" in msg or "insufficient_balance" in msg:
        return "credits_exhausted"
    if "rate_limit" in msg or "429" in msg or "too many requests" in msg:
        return "rate_limited"
    if "401" in msg or "authentication" in msg or "invalid x-api-key" in msg:
        return "auth_error"
    if "anthropic" in msg.lower() and ("error" in msg.lower() or "badrequest" in msg.lower()):
        return "anthropic_error"
    return None


async def _record_anthropic_error(error_type: str, error_message: str):
    """Record Anthropic error to source_fetches."""
    global _anthropic_error_count, _LAST_ANTHROPIC_ERROR_AT
    _anthropic_error_count += 1
    from datetime import datetime, timezone

    _LAST_ANTHROPIC_ERROR_AT = datetime.now(timezone.utc).isoformat()
    try:
        from app.ingestion.source_fetch import record_source_fetch_async

        await record_source_fetch_async(
            provider="anthropic",
            target_type="tag_patent",
            status="blocked",
            error_message=f"{error_type}: {error_message[:500]}",
        )
    except Exception:
        logger.debug("Failed to record Anthropic error to source_fetches", exc_info=True)


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
    async with async_session_maker() as session:
        result = await session.execute(
            select(PatentPublication).where(PatentPublication.id == UUID(patent_id))
        )
        patent = result.scalar_one_or_none()
        if not patent:
            return {"status": "failed", "error": "patent not found"}

        if not patent.title and not patent.abstract:
            return {"status": "skipped", "reason": "no_content"}

        tags, artifact_id = await cached_tag_patent(
            session,
            patent,
            run_id=UUID(run_id) if run_id else None,
        )
        # Reset error counter on success
        global _anthropic_error_count
        _anthropic_error_count = 0
        patent.tags = tags
        patent.latest_tags_artifact_id = artifact_id
        await session.commit()
        if run_id:
            await recompute_run_aggregates(session, run_id)
        return {
            "status": "success",
            "artifact_id": str(artifact_id),
            "tag_count": sum(len(v) if isinstance(v, list) else 0 for v in tags.values()),
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
        except Exception as e:
            error_type = _is_anthropic_error(e)
            if error_type:
                logger.error("Anthropic API error during tagging: %s — %s", error_type, e)
                await _record_anthropic_error(error_type, str(e))
                stats["failed"] += 1
                # Circuit-break: stop batch on 3 consecutive Anthropic errors
                if (
                    error_type == "credits_exhausted"
                    and _anthropic_error_count >= ANTHROPIC_ERROR_MAX_CONSECUTIVE
                ):
                    logger.critical(
                        "Tag batch HALTED after %d consecutive Anthropic credit errors. "
                        "Waiting for next beat cycle.",
                        _anthropic_error_count,
                    )
                    break
            else:
                stats["failed"] += 1
                logger.exception("tag failed for %s: %s", patent.id, e)
        stats["processed"] += 1
    return stats
