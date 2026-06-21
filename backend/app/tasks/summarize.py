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

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.summarize.summarize_patent",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(SummarizationError,),
)
def summarize_patent(self, patent_id: str, force: bool = False) -> dict:
    """Generate AI summary for a single patent."""
    logger.info(f"Starting summarization for patent {patent_id} (force={force})")
    try:
        result = asyncio.run(_summarize_patent_async(patent_id, force=force))
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
    """Summarize all patents that haven't been summarized yet.

    Uses a SINGLE event loop for the entire batch to avoid
    "Event loop is closed / Future attached to a different loop" errors.
    """
    batch_limit = limit or settings.summarization_batch_size
    logger.info(f"Starting batch summarization (limit: {batch_limit})")
    return asyncio.run(_batch_summarize_async(batch_limit))


@celery_app.task(
    bind=True,
    name="app.tasks.summarize.batch_resummarize_enriched",
    max_retries=1,
)
def batch_resummarize_enriched(self, limit: int | None = None) -> dict:
    """Re-summarize patents that have abstracts but were previously summarized
    with title-only (low quality). Single event loop for the entire batch.
    """
    batch_limit = limit or settings.summarization_batch_size
    logger.info(f"Starting re-summarization of enriched patents (limit: {batch_limit})")
    return asyncio.run(_batch_resummarize_async(batch_limit))


# ── Async batch runners (single event loop each) ──────────────────────


async def _batch_summarize_async(limit: int) -> dict:
    """Process a batch of unsummarized patents in one event loop."""
    patents = await _get_pending_patents(limit)
    stats = {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}

    for patent in patents:
        try:
            result = await _summarize_patent_async(str(patent.id))
            if result["status"] == "success":
                stats["succeeded"] += 1
            elif result["status"] == "skipped":
                stats["skipped"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:
            stats["failed"] += 1
            logger.warning(f"Batch summarization failed for {patent.id}: {e}")

        stats["processed"] += 1

    logger.info(f"Batch summarization complete: {stats}")
    return stats


async def _batch_resummarize_async(limit: int) -> dict:
    """Re-summarize enriched patents in one event loop."""
    patents = await _get_enriched_resummarize_candidates(limit)
    stats = {"processed": 0, "succeeded": 0, "failed": 0, "total_candidates": len(patents)}

    for patent in patents:
        try:
            result = await _summarize_patent_async(str(patent.id), force=True)
            if result["status"] == "success":
                stats["succeeded"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:
            stats["failed"] += 1
            logger.warning(f"Re-summarization failed for {patent.id}: {e}")

        stats["processed"] += 1

    logger.info(f"Re-summarization complete: {stats}")
    return stats


# ── Async helpers ─────────────────────────────────────────────────────


async def _summarize_patent_async(patent_id: str, force: bool = False) -> dict:
    """Summarize a single patent using the cached LLM pipeline."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(PatentPublication).where(PatentPublication.id == UUID(patent_id))
        )
        patent = result.scalar_one_or_none()

        if not patent:
            logger.warning(f"Patent {patent_id} not found")
            return {"status": "failed", "error": "Patent not found"}

        if patent.summarized_at and not force:
            logger.debug(f"Patent {patent_id} already summarized")
            return {"status": "skipped", "reason": "already_summarized"}

        if not patent.title and not patent.abstract:
            logger.warning(f"Patent {patent_id} has no title or abstract")
            return {"status": "skipped", "reason": "no_content"}

        summary, artifact_id = await cached_summarize_patent(session, patent)

        patent.summary = summary
        patent.novel_applications = [
            app["application"] for app in summary.get("novel_applications", [])
        ]
        patent.summarized_at = datetime.utcnow()
        patent.latest_summary_artifact_id = artifact_id

        await session.commit()

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


async def _get_enriched_resummarize_candidates(limit: int) -> list[PatentPublication]:
    """Get patents with abstracts that were summarized before abstract was added."""
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
