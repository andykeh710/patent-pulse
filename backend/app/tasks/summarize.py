import asyncio
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.ai.summarizer import PatentSummarizer
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
def summarize_patent(self, patent_id: str) -> dict:
    """
    Generate AI summary for a single patent.

    Args:
        patent_id: UUID of the patent to summarize

    Returns:
        Dict with status and summary keys
    """
    logger.info(f"Starting summarization for patent {patent_id}")

    try:
        result = asyncio.run(_summarize_patent_async(patent_id))
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


async def _summarize_patent_async(patent_id: str) -> dict:
    """Async helper for patent summarization."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(PatentPublication).where(PatentPublication.id == UUID(patent_id))
        )
        patent = result.scalar_one_or_none()

        if not patent:
            logger.warning(f"Patent {patent_id} not found")
            return {"status": "failed", "error": "Patent not found"}

        if patent.summarized_at:
            logger.debug(f"Patent {patent_id} already summarized")
            return {"status": "skipped", "reason": "already_summarized"}

        if not patent.title and not patent.abstract:
            logger.warning(f"Patent {patent_id} has no title or abstract")
            return {"status": "skipped", "reason": "no_content"}

        summarizer = PatentSummarizer(
            api_key=settings.anthropic_api_key,
            model=settings.claude_model,
        )

        summary = summarizer.summarize(patent)

        patent.summary = summary
        patent.novel_applications = [
            app["application"] for app in summary.get("novel_applications", [])
        ]
        patent.summarized_at = datetime.utcnow()

        await session.commit()

        logger.info(f"Successfully summarized patent {patent_id}")
        return {"status": "success", "summary": summary}


async def _get_pending_patents(limit: int) -> list[PatentPublication]:
    """Get patents awaiting summarization."""
    async with async_session_maker() as session:
        return await get_unsummarized_patents(session, limit=limit)
