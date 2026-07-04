"""
Patent Content Enrichment Tasks.

Fetches patent abstracts AND claims from EPO OPS for patents that are missing them.
This is critical for generating high-quality AI summaries — without abstracts and claims,
summaries are based on title only and are very low quality.

EPO OPS rate limits (free tier): ~200 requests/minute for retrieval.
Each patent needs 2 API calls (abstract + claims), so we throttle at ~0.5s per call.

Key design decision: commits every COMMIT_CHUNK patents to avoid DB transaction timeouts.
Previous implementation committed only at the end of a batch — this caused hangs on large runs.
"""

import asyncio
import logging
import time
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select, update

from app.config import settings
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.ingestion.epo_client import EPOClient
from app.ingestion.google_patents_client import GooglePatentsClient
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

THROTTLE_DELAY = 0.5  # seconds between EPO API calls (~120/min)
COMMIT_CHUNK = 25  # commit to DB every N patents to avoid transaction timeouts


@celery_app.task(
    bind=True,
    name="app.tasks.enrich_abstracts.enrich_batch",
    max_retries=2,
    default_retry_delay=60,
)
def enrich_batch(self, batch_size: int = 500) -> dict:
    """
    Fetch abstracts and claims from EPO OPS + Google Patents for patents missing content.

    Uses a Redis distributed lock to ensure only one batch runs at a time across
    all workers. Concurrent batches detect the lock and exit cleanly without
    duplicating work.

    Args:
        batch_size: Number of patents to process per run

    Returns:
        Stats dict with enriched/failed/skipped counts
    """
    if not settings.epo_ops_client_id or not settings.epo_ops_client_secret:
        logger.warning("EPO OPS credentials not configured, skipping enrichment")
        return {"skipped": True, "reason": "EPO credentials not configured"}

    # Acquire a Redis lock to serialize enrichment batches.
    # Lock TTL is generous (1 hour) — celery's task timeout will release it
    # naturally if the worker crashes.
    import redis as redis_lib

    redis_client = redis_lib.Redis.from_url(settings.redis_url)
    lock_key = "enrich_batch:lock"
    lock_ttl_seconds = 3600  # 1 hour max — covers worst-case batch_size=500
    lock_acquired = redis_client.set(lock_key, "1", nx=True, ex=lock_ttl_seconds)

    if not lock_acquired:
        logger.info(
            "enrich_batch lock held by another worker; this batch will exit cleanly. "
            "Re-queue if you want it to run later."
        )
        return {"skipped": True, "reason": "another batch is running"}

    try:
        logger.info(f"Starting content enrichment batch (size={batch_size})")
        stats = asyncio.run(_enrich_batch_async(batch_size))
        logger.info(f"Enrichment complete: {stats}")
        return stats
    finally:
        redis_client.delete(lock_key)
        try:
            redis_client.close()
        except Exception:
            pass


@celery_app.task(
    bind=True,
    name="app.tasks.enrich_abstracts.enrich_single",
)
def enrich_single(self, patent_id: str) -> dict:
    """Enrich a single patent with abstract and claims."""
    if not settings.epo_ops_client_id or not settings.epo_ops_client_secret:
        return {"skipped": True, "reason": "EPO credentials not configured"}

    result = asyncio.run(_enrich_single_async(patent_id))
    return result


async def _enrich_batch_async(batch_size: int) -> dict:
    """
    Fetch abstracts and claims for a batch of patents.
    Commits every COMMIT_CHUNK patents to avoid transaction timeouts.
    """
    stats = {
        "processed": 0,
        "abstracts_added": 0,
        "claims_added": 0,
        "descriptions_added": 0,
        "no_content_available": 0,
        "failed": 0,
        "remaining": 0,
    }

    # Phase 1: Get list of patents needing enrichment.
    # Priority order:
    #   1. Patents expiring soonest (highest commercial urgency)
    #   2. Highest interesting_score
    #   3. Most recent publications (freshness)
    # We rely on a global Redis lock (acquired by the caller) to ensure only one
    # enrich_batch runs at a time, so we don't need row-level claim coordination.
    async with async_session_maker() as session:
        result = await session.execute(
            select(
                PatentPublication.id,
                PatentPublication.publication_number,
                PatentPublication.kind_code,
            )
            .where(
                or_(
                    PatentPublication.abstract.is_(None),
                    PatentPublication.claims_text.is_(None),
                    PatentPublication.description_text.is_(None),
                )
            )
            .order_by(
                PatentPublication.estimated_expiry_date.asc().nullslast(),
                PatentPublication.interesting_score.desc().nullslast(),
                PatentPublication.publication_date.desc().nullslast(),
            )
            .limit(batch_size)
        )
        patents = list(result.all())

        count_result = await session.execute(
            select(func.count(PatentPublication.id)).where(
                or_(
                    PatentPublication.abstract.is_(None),
                    PatentPublication.claims_text.is_(None),
                    PatentPublication.description_text.is_(None),
                )
            )
        )
        total_remaining = count_result.scalar() or 0

    if not patents:
        logger.info("No patents need content enrichment")
        return stats

    stats["remaining"] = max(0, total_remaining - len(patents))
    logger.info(
        f"Enriching {len(patents)} patents, ~{stats['remaining']} remaining after this batch"
    )

    # Phase 2: Fetch content and update DB in small committed chunks
    # Strategy: EPO OPS for abstracts (fast, reliable for US patents)
    #           Google Patents for claims + description (scraping, needs rate limiting)
    # After each chunk commits, queue summarization for patents that gained an abstract.
    from app.tasks.summarize import summarize_patent

    stats["summarization_queued"] = 0

    with EPOClient() as epo_client, GooglePatentsClient() as gp_client:
        for chunk_start in range(0, len(patents), COMMIT_CHUNK):
            chunk = patents[chunk_start : chunk_start + COMMIT_CHUNK]
            queued_for_summary: list[str] = []

            async with async_session_maker() as session:
                for patent_id, pub_number, kind_code in chunk:
                    try:
                        values = {"updated_at": datetime.utcnow()}
                        got_content = False
                        got_abstract = False

                        # Source 1: EPO OPS for abstract
                        abstract = epo_client.fetch_abstract_for_us_patent(pub_number)
                        time.sleep(THROTTLE_DELAY)

                        if abstract:
                            values["abstract"] = abstract
                            values["abstract_source"] = "epo_ops"
                            stats["abstracts_added"] += 1
                            got_content = True
                            got_abstract = True

                        # Source 2: Google Patents for claims + description
                        gp_data = gp_client.fetch_patent_fulltext(pub_number, kind_code or "B2")
                        time.sleep(THROTTLE_DELAY)

                        if gp_data.get("claims_text"):
                            values["claims_text"] = gp_data["claims_text"]
                            values["claims_source"] = "google_patents"
                            stats["claims_added"] += 1
                            got_content = True

                        if gp_data.get("description_text"):
                            values["description_text"] = gp_data["description_text"]
                            stats["descriptions_added"] += 1
                            got_content = True

                        # If EPO didn't have abstract, try Google Patents
                        if not abstract and gp_data.get("abstract"):
                            values["abstract"] = gp_data["abstract"]
                            values["abstract_source"] = "google_patents"
                            stats["abstracts_added"] += 1
                            got_content = True
                            got_abstract = True

                        if got_content:
                            await session.execute(
                                update(PatentPublication)
                                .where(PatentPublication.id == patent_id)
                                .values(**values)
                            )
                            # Queue summarization if we obtained an abstract
                            # (force=True so existing title-only summaries get refreshed)
                            if got_abstract:
                                queued_for_summary.append(str(patent_id))
                        else:
                            stats["no_content_available"] += 1

                    except Exception as e:
                        stats["failed"] += 1
                        logger.warning(f"Failed to enrich {pub_number}: {e}")

                    stats["processed"] += 1

                await session.commit()

            # After chunk commit, queue summarization tasks for patents that gained an abstract
            for pid in queued_for_summary:
                summarize_patent.delay(pid, force=True)
                stats["summarization_queued"] += 1

            # Progress log every chunk
            logger.info(
                f"  Progress: {stats['processed']}/{len(patents)} "
                f"(abstracts={stats['abstracts_added']}, claims={stats['claims_added']}, "
                f"descriptions={stats['descriptions_added']}, failed={stats['failed']})"
            )

    return stats


async def _enrich_single_async(patent_id: str) -> dict:
    """Enrich a single patent with abstract, claims, and description."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(PatentPublication).where(PatentPublication.id == UUID(patent_id))
        )
        patent = result.scalar_one_or_none()

        if not patent:
            return {"error": "Patent not found"}

        if patent.abstract and patent.claims_text and patent.description_text:
            return {"status": "skipped", "reason": "already_has_full_content"}

        updated = {}

        # Source 1: EPO OPS for abstract
        if not patent.abstract:
            with EPOClient() as epo_client:
                abstract = epo_client.fetch_abstract_for_us_patent(patent.publication_number)
            if abstract:
                patent.abstract = abstract
                updated["abstract"] = len(abstract)

        # Source 2: Google Patents for claims + description (and abstract fallback)
        if not patent.claims_text or not patent.description_text:
            with GooglePatentsClient() as gp_client:
                gp_data = gp_client.fetch_patent_fulltext(
                    patent.publication_number, patent.kind_code or "B2"
                )

            if gp_data.get("claims_text") and not patent.claims_text:
                patent.claims_text = gp_data["claims_text"]
                updated["claims_text"] = len(gp_data["claims_text"])

            if gp_data.get("description_text") and not patent.description_text:
                patent.description_text = gp_data["description_text"]
                updated["description_text"] = len(gp_data["description_text"])

            if gp_data.get("abstract") and not patent.abstract:
                patent.abstract = gp_data["abstract"]
                updated["abstract"] = len(gp_data["abstract"])

        if updated:
            patent.updated_at = datetime.utcnow()
            await session.commit()
            return {"status": "enriched", "updated_fields": updated}
        else:
            return {"status": "no_content_available"}
