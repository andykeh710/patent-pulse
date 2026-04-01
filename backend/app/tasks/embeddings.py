"""
Embedding Generation Tasks.

Generates vector embeddings for patents to enable semantic search
and novelty scoring.
"""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.ai.embedder import EmbeddingError, PatentEmbedder
from app.core.models import PatentPublication
from app.database import async_session_maker
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
def batch_generate_embeddings(self, limit: int = 50) -> dict:
    """
    Generate embeddings for patents missing them.

    Args:
        limit: Maximum patents to process

    Returns:
        Stats dict with succeeded/failed counts
    """
    logger.info(f"Starting batch embedding generation (limit: {limit})")

    stats = asyncio.run(_batch_generate_embeddings_async(limit))

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


async def _batch_generate_embeddings_async(limit: int) -> dict:
    """Generate embeddings for patents missing them."""
    stats = {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}

    async with async_session_maker() as session:
        result = await session.execute(
            select(PatentPublication)
            .where(PatentPublication.embedding.is_(None))
            .where(PatentPublication.title.isnot(None))
            .order_by(PatentPublication.created_at.desc())
            .limit(limit)
        )
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
