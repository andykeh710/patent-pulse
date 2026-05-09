import asyncio
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.ai.summarizer import summarize_patent as cached_summarize_patent
from app.config import settings
from app.core.exceptions import SummarizationError
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.ingestion.dedup import get_unsummarized_patents
from app.tasks.celery_app import celery_app
from app.tasks.run_aggregates import (
    recompute_run_aggregates,
    record_run_task_completion,
    record_run_task_failure,
)

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.summarize.summarize_patent",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(SummarizationError,),
)
def summarize_patent(
    self, patent_id: str, force: bool = False, run_id: str | None = None
) -> dict:
    """
    Generate AI summary for a single patent.

    Args:
        patent_id: UUID of the patent to summarize
        force: If True, re-summarize even if already summarized

    Returns:
        Dict with status and summary keys
    """
    logger.info(f"Starting summarization for patent {patent_id} (force={force})")

    try:
        result = asyncio.run(
            _summarize_patent_async(patent_id, force=force, run_id=run_id)
        )
        return result
    except SummarizationError as e:
        logger.warning(f"Summarization failed for {patent_id}, retrying: {e}")
        raise
    except Exception as e:
        logger.error(f"Summarization failed for {patent_id}: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(
    bind=True,
    name="app.tasks.summarize.batch_summarize_pending",
    max_retries=1,
)
def batch_summarize_pending(self, limit: int | None = None) -> dict:
    """
    Summarize all patents that haven't been summarized yet.

    Args:
        limit: Maximum number of patents to process. Defaults to settings.summarization_batch_size.

    Returns:
        Stats dict with processed, succeeded, failed counts.
    """
    batch_limit = limit or settings.summarization_batch_size
    logger.info(f"Starting batch summarization (limit: {batch_limit})")

    patents = asyncio.run(_get_pending_patents(batch_limit))

    stats = {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}

    for patent in patents:
        try:
            result = asyncio.run(_summarize_patent_async(str(patent.id)))
            if result["status"] == "success":
                stats["succeeded"] += 1
            elif result["status"] == "skipped":
                stats["skipped"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:
            stats["failed"] += 1
            logger.error(f"Batch summarization failed for {patent.id}: {e}")

        stats["processed"] += 1

    logger.info(f"Batch summarization complete: {stats}")
    return stats


@celery_app.task(
    bind=True,
    name="app.tasks.summarize.batch_resummarize_enriched",
    max_retries=1,
)
def batch_resummarize_enriched(self, limit: int | None = None) -> dict:
    """
    Re-summarize patents that have abstracts but were previously summarized
    with title-only (low quality). Targets patents where abstract was added
    after initial summarization.

    Args:
        limit: Maximum number of patents to process.

    Returns:
        Stats dict with processed, succeeded, failed counts.
    """
    batch_limit = limit or settings.summarization_batch_size
    logger.info(f"Starting re-summarization of enriched patents (limit: {batch_limit})")

    patents = asyncio.run(_get_enriched_resummarize_candidates(batch_limit))

    stats = {"processed": 0, "succeeded": 0, "failed": 0, "total_candidates": len(patents)}

    for patent in patents:
        try:
            result = asyncio.run(_summarize_patent_async(str(patent.id), force=True))
            if result["status"] == "success":
                stats["succeeded"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:
            stats["failed"] += 1
            logger.error(f"Re-summarization failed for {patent.id}: {e}")

        stats["processed"] += 1

    logger.info(f"Re-summarization complete: {stats}")
    return stats


async def _get_enriched_resummarize_candidates(limit: int) -> list[PatentPublication]:
    """Get patents that have abstracts but were summarized before the abstract was added."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(PatentPublication)
            .where(PatentPublication.abstract.isnot(None))
            .where(PatentPublication.summarized_at.isnot(None))
            .where(PatentPublication.updated_at > PatentPublication.summarized_at)
            .order_by(PatentPublication.interesting_score.desc().nullslast())
            .limit(limit)
        )
        return list(result.scalars().all())


async def _summarize_patent_async(
    patent_id: str, force: bool = False, run_id: str | None = None
) -> dict:
    """Async helper for patent summarization.

    Routes through :func:`app.ai.summarizer.summarize_patent` so every
    summary is cached as an ``AIArtifact(summary)`` row and the patent's
    ``latest_summary_artifact_id`` is updated for fast denormalized reads.
    """
    run_uuid = UUID(run_id) if run_id else None
    async with async_session_maker() as session:
        result = await session.execute(
            select(PatentPublication).where(PatentPublication.id == UUID(patent_id))
        )
        patent = result.scalar_one_or_none()

        if not patent:
            logger.warning(f"Patent {patent_id} not found")
            if run_uuid:
                await record_run_task_failure(session, run_uuid)
                await recompute_run_aggregates(session, run_uuid)
            return {"status": "failed", "error": "Patent not found"}

        if patent.summarized_at and not force:
            logger.debug(f"Patent {patent_id} already summarized")
            if run_uuid:
                await record_run_task_completion(session, run_uuid)
                await recompute_run_aggregates(session, run_uuid)
            return {"status": "skipped", "reason": "already_summarized"}

        if not patent.title and not patent.abstract:
            logger.warning(f"Patent {patent_id} has no title or abstract")
            if run_uuid:
                await record_run_task_completion(session, run_uuid)
                await recompute_run_aggregates(session, run_uuid)
            return {"status": "skipped", "reason": "no_content"}

        summary, artifact_id = await cached_summarize_patent(
            session,
            patent,
            run_id=run_uuid,
        )

        patent.summary = summary
        patent.novel_applications = [
            app["application"] for app in summary.get("novel_applications", [])
        ]
        patent.summarized_at = datetime.utcnow()
        patent.latest_summary_artifact_id = artifact_id

        await session.commit()
        if run_uuid:
            await record_run_task_completion(session, run_uuid)
            await recompute_run_aggregates(session, run_uuid)

        logger.info(f"Successfully summarized patent {patent_id}")
        return {
            "status": "success",
            "summary": summary,
            "artifact_id": str(artifact_id),
        }


async def _get_pending_patents(limit: int) -> list[PatentPublication]:
    """Get patents awaiting summarization."""
    async with async_session_maker() as session:
        return await get_unsummarized_patents(session, limit=limit)
