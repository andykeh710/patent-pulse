"""
Embedding Generation Tasks.

Generates vector embeddings for patents to enable semantic search
and novelty scoring.
"""

import asyncio
import logging
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select

from app.ai.embedder import EmbeddingError, PatentEmbedder
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.database import engine as _engine
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.embeddings.generate_patent_embedding",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(EmbeddingError,),
)
def generate_patent_embedding(self, patent_id: str) -> dict:
    """
    Generate embedding for a single patent.

    Args:
        patent_id: UUID of the patent

    Returns:
        Status dict with success/error info
    """
    logger.info(f"Generating embedding for patent {patent_id}")

    try:
        result = asyncio.run(_generate_embedding_async(patent_id))
        return result
    except EmbeddingError as e:
        logger.warning(f"Embedding failed for {patent_id}, retrying: {e}")
        raise
    except Exception as e:
        logger.error(f"Embedding failed for {patent_id}: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(
    bind=True,
    name="app.tasks.embeddings.batch_generate_embeddings",
    max_retries=1,
)
def batch_generate_embeddings(
    self,
    limit: int = 50,
    prioritize_expiring: bool = False,
    expiring_window_days: int = 730,
) -> dict:
    """
    Generate embeddings for patents missing them.

    Args:
        limit: Maximum patents to process.
        prioritize_expiring: When True, restrict the query to patents
            whose estimated_expiry_date falls within the next
            ``expiring_window_days`` days and order by expiry-soonest first.
            Used by the Sprint 5 follow-up beat schedule to ensure the
            Expiry Radar cohort acquires embeddings (and therefore usage
            signals) — the default newest-first ordering otherwise leaves
            them perpetually unembedded.
        expiring_window_days: Look-ahead window when ``prioritize_expiring``
            is set. Defaults to 730 (2 years), matching the Expiry Radar
            default view.

    Returns:
        Stats dict with succeeded/failed counts.
    """
    logger.info(
        "Starting batch embedding generation (limit=%d, prioritize_expiring=%s)",
        limit,
        prioritize_expiring,
    )

    async def _run_and_dispose():
        try:
            return await _batch_generate_embeddings_async(
                limit,
                prioritize_expiring=prioritize_expiring,
                expiring_window_days=expiring_window_days,
            )
        finally:
            # Force-close any connections checked out by this asyncio.run loop.
            # Without this, the embedder's synchronous OpenAI calls (which block
            # the loop for several seconds) can leave the SELECT transaction
            # idle-in-transaction across Celery task boundaries, accumulating
            # leaked connections every */2 min cron firing.
            await _engine.dispose()

    stats = asyncio.run(_run_and_dispose())

    logger.info(f"Batch embedding complete: {stats}")
    return stats


async def _generate_embedding_async(patent_id: str) -> dict:
    """Generate embedding for a single patent."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(PatentPublication).where(PatentPublication.id == UUID(patent_id))
        )
        patent = result.scalar_one_or_none()

        if not patent:
            return {"status": "failed", "error": "Patent not found"}

        if patent.embedding is not None:
            return {"status": "skipped", "reason": "already_embedded"}

        if not patent.title and not patent.abstract:
            return {"status": "skipped", "reason": "no_content"}

        with PatentEmbedder() as embedder:
            embedding = embedder.generate_patent_embedding(patent)

        patent.embedding = embedding
        await session.commit()

        logger.info(f"Successfully generated embedding for {patent.doc_id}")
        return {"status": "success", "dimensions": len(embedding)}


async def _batch_generate_embeddings_async(
    limit: int,
    *,
    prioritize_expiring: bool = False,
    expiring_window_days: int = 730,
) -> dict:
    """Generate embeddings for patents missing them."""
    stats = {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}

    async with async_session_maker() as session:
        query = (
            select(PatentPublication)
            .where(PatentPublication.embedding.is_(None))
            .where(PatentPublication.title.isnot(None))
        )

        if prioritize_expiring:
            today = date.today()
            horizon = today + timedelta(days=expiring_window_days)
            query = (
                query.where(PatentPublication.estimated_expiry_date.isnot(None))
                .where(PatentPublication.estimated_expiry_date >= today)
                .where(PatentPublication.estimated_expiry_date <= horizon)
                .order_by(PatentPublication.estimated_expiry_date.asc())
            )
        else:
            query = query.order_by(PatentPublication.created_at.desc())

        result = await session.execute(query.limit(limit))
        patents = result.scalars().all()

        if not patents:
            return stats

        with PatentEmbedder() as embedder:
            for patent in patents:
                try:
                    if not patent.title and not patent.abstract:
                        stats["skipped"] += 1
                        continue

                    embedding = embedder.generate_patent_embedding(patent)
                    patent.embedding = embedding
                    stats["succeeded"] += 1

                except EmbeddingError as e:
                    logger.warning(f"Embedding failed for {patent.doc_id}: {e}")
                    stats["failed"] += 1
                except Exception as e:
                    logger.error(f"Unexpected error for {patent.doc_id}: {e}")
                    stats["failed"] += 1

                stats["processed"] += 1

        await session.commit()

    return stats
