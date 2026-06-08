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
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedder import EmbeddingError, PatentEmbedder
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.database import engine as _engine
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# ── Chunk size for batch embedding ─────────────────────────────
# OpenAI accepts up to 2048 texts per call; 20 keeps each chunk's
# transaction short (< 5 seconds) to stay within the 60s
# idle_in_transaction_session_timeout.
CHUNK_SIZE = 20


@celery_app.task(
    bind=True,
    name="app.tasks.embeddings.generate_patent_embedding",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(EmbeddingError,),
)
def generate_patent_embedding(self, patent_id: str) -> dict:
    """Generate embedding for a single patent."""
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
    """Generate embeddings for patents missing them.

    Processes patents in chunks of CHUNK_SIZE using OpenAI's batch
    embedding API. Each chunk commits immediately to keep transaction
    duration under the idle_in_transaction_session_timeout.

    Args:
        limit: Maximum patents to process.
        prioritize_expiring: When True, prioritize patents expiring soon.
        expiring_window_days: Look-ahead window for expiring filter.
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


# ── Text builders (extracted from PatentEmbedder for reuse) ────


def _build_patent_text(patent: PatentPublication) -> str | None:
    """Build the embeddable text for a patent. Returns None if empty."""
    text_parts = []

    if patent.title:
        text_parts.append(f"Title: {patent.title}")

    if patent.abstract:
        text_parts.append(f"Abstract: {patent.abstract}")

    if patent.claims_text:
        independent = _extract_independent_claims(patent.claims_text)
        if independent:
            text_parts.append(f"Claims: {independent}")

    if patent.cpc:
        text_parts.append(f"Classifications: {', '.join(patent.cpc[:5])}")

    combined = "\n\n".join(text_parts)
    return combined if combined.strip() else None


def _extract_independent_claims(claims_text: str, max_length: int = 2000) -> str:
    """Extract independent claims from full claims text."""
    import re

    lines = claims_text.split("\n")
    independent = []
    current_claim = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        claim_start = re.match(r"^(\d+)\.\s*", line)
        if claim_start:
            if current_claim:
                claim_text = " ".join(current_claim)
                if not _references_other_claim(claim_text):
                    independent.append(claim_text)
            current_claim = [line]
        else:
            current_claim.append(line)

    if current_claim:
        claim_text = " ".join(current_claim)
        if not _references_other_claim(claim_text):
            independent.append(claim_text)

    result = "\n".join(independent[:3])
    return result[:max_length]


def _references_other_claim(claim_text: str) -> bool:
    """Check if claim references another claim."""
    import re

    first_100 = claim_text[:100].lower()
    patterns = [
        r"claim\s+\d+",
        r"according to claim",
        r"as (claimed|defined) in claim",
    ]
    return any(re.search(p, first_100) for p in patterns)


# ── Batch backfill (production path) ───────────────────────────


async def _batch_generate_embeddings_async(
    limit: int,
    *,
    prioritize_expiring: bool = False,
    expiring_window_days: int = 730,
) -> dict:
    """Generate embeddings for patents missing them (production path).

    Creates its own session via async_session_maker().
    """
    async with async_session_maker() as session:
        return await _run_batch(
            session,
            limit,
            prioritize_expiring=prioritize_expiring,
            expiring_window_days=expiring_window_days,
        )


# ── Batch backfill (testable path) ─────────────────────────────


async def _batch_generate_embeddings_for_session(
    session: AsyncSession,
    limit: int,
    *,
    prioritize_expiring: bool = False,
    expiring_window_days: int = 730,
) -> dict:
    """Generate embeddings for patents missing them (test path).

    Accepts a pre-existing session so tests can seed patent data
    and verify the backfill in the same transaction.
    """
    return await _run_batch(
        session,
        limit,
        prioritize_expiring=prioritize_expiring,
        expiring_window_days=expiring_window_days,
    )


# ── Core batch logic ───────────────────────────────────────────


async def _run_batch(
    session: AsyncSession,
    limit: int,
    *,
    prioritize_expiring: bool = False,
    expiring_window_days: int = 730,
) -> dict:
    """Core batch embedding logic. Commits after each chunk of CHUNK_SIZE."""
    stats = {"processed": 0, "succeeded": 0, "failed": 0, "skipped": 0}

    # ── Fetch patents needing embeddings ──────────────────────────
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

    # ── Build text for each patent ────────────────────────────────
    patent_texts: list[tuple[PatentPublication, str]] = []
    for patent in patents:
        text = _build_patent_text(patent)
        if text:
            patent_texts.append((patent, text))
        else:
            stats["skipped"] += 1

    if not patent_texts:
        return stats

    # ── Embed in chunks, commit after each ────────────────────────
    with PatentEmbedder() as embedder:
        for i in range(0, len(patent_texts), CHUNK_SIZE):
            chunk = patent_texts[i : i + CHUNK_SIZE]
            texts = [t for _, t in chunk]

            try:
                embeddings = embedder.generate_batch_embeddings(texts)
            except EmbeddingError as e:
                logger.warning(
                    "Chunk %d/%d embedding failed: %s",
                    i // CHUNK_SIZE + 1,
                    (len(patent_texts) + CHUNK_SIZE - 1) // CHUNK_SIZE,
                    e,
                )
                stats["failed"] += len(chunk)
                await session.commit()
                continue
            except Exception as e:
                logger.error("Unexpected error in chunk: %s", e)
                stats["failed"] += len(chunk)
                await session.commit()
                continue

            # Apply embeddings to patents
            for (patent, _), emb in zip(chunk, embeddings):
                if emb is None:
                    stats["failed"] += 1
                    continue
                patent.embedding = emb
                stats["succeeded"] += 1

            stats["processed"] += len(chunk)

            # Commit this chunk immediately — keeps the transaction
            # short so idle_in_transaction_session_timeout never fires.
            await session.commit()

    logger.info(
        "Batch done: processed=%d succeeded=%d failed=%d skipped=%d",
        stats["processed"],
        stats["succeeded"],
        stats["failed"],
        stats["skipped"],
    )

    return stats
