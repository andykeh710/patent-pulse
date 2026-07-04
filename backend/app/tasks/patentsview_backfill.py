"""
PatentsView backfill tasks.

Fetches abstracts and claims from USPTO PatentsView API for patents
missing content. Complements the existing EPO OPS + Google Patents pipeline
with a free, rate-limited USPTO source.

Schedule: 4x/day (00:00, 06:00, 12:00, 18:00 UTC).
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import func, or_, select, update

from app.core.models import PatentPublication
from app.database import async_session_maker
from app.ingestion.patentsview_client import PatentsViewClient
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

COMMIT_CHUNK = 50


@celery_app.task(
    bind=True,
    name="app.tasks.enrich_abstracts.backfill_patentsview",
    max_retries=2,
    default_retry_delay=300,
)
def backfill_patentsview(self, batch_size: int = 200) -> dict:
    """Fetch abstracts and claims from PatentsView for patents missing content.

    Prioritizes high-value patents: those with opportunity_score > 50
    or tagged with any user topic, then falls back to newest patents.
    """
    logger.info("Starting PatentsView backfill (batch_size=%d)", batch_size)
    stats = asyncio.run(_backfill_patentsview_async(batch_size))
    logger.info("PatentsView backfill complete: %s", stats)
    return stats


async def _backfill_patentsview_async(batch_size: int) -> dict:
    stats = {
        "processed": 0,
        "abstracts_added": 0,
        "claims_added": 0,
        "no_data": 0,
        "failed": 0,
        "remaining": 0,
    }

    # Select patents needing content, prioritizing high-value ones
    async with async_session_maker() as session:
        result = await session.execute(
            select(
                PatentPublication.id,
                PatentPublication.publication_number,
            )
            .where(
                or_(
                    PatentPublication.abstract.is_(None),
                    PatentPublication.claims_text.is_(None),
                )
            )
            .order_by(
                PatentPublication.opportunity_score.desc().nullslast(),
                PatentPublication.interesting_score.desc().nullslast(),
            )
            .limit(batch_size)
        )
        patents = [(row[0], row[1]) for row in result.all()]

        count_result = await session.execute(
            select(func.count(PatentPublication.id)).where(
                or_(
                    PatentPublication.abstract.is_(None),
                    PatentPublication.claims_text.is_(None),
                )
            )
        )
        stats["remaining"] = max(0, (count_result.scalar() or 0) - len(patents))

    if not patents:
        logger.info("No patents need PatentsView enrichment")
        return stats

    logger.info(
        "PatentsView enriching %d patents, ~%d remaining",
        len(patents),
        stats["remaining"],
    )

    # Fetch in bulk chunks to minimize API calls
    pub_numbers = [pn for _, pn in patents]
    with PatentsViewClient() as client:
        for chunk_start in range(0, len(pub_numbers), COMMIT_CHUNK):
            chunk_pubs = pub_numbers[chunk_start : chunk_start + COMMIT_CHUNK]
            chunk_ids = [
                patents[pub_numbers.index(pn)][0] for pn in chunk_pubs if pn in pub_numbers
            ]

            # Bulk fetch for this chunk
            bulk_data = client.fetch_bulk(chunk_pubs)

            async with async_session_maker() as session:
                for patent_id, pub_number in zip(chunk_ids, chunk_pubs):
                    try:
                        pdata = bulk_data.get(pub_number)
                        if not pdata or (not pdata.abstract and not pdata.claims):
                            stats["no_data"] += 1
                            stats["processed"] += 1
                            continue

                        values = {"updated_at": datetime.now(timezone.utc)}
                        got_abstract = False

                        if pdata.abstract:
                            values["abstract"] = pdata.abstract
                            values["abstract_source"] = "patentsview"
                            stats["abstracts_added"] += 1
                            got_abstract = True

                        if pdata.claims and len(pdata.claims) > 50:
                            values["claims_text"] = pdata.claims
                            values["claims_source"] = "patentsview"
                            stats["claims_added"] += 1

                        await session.execute(
                            update(PatentPublication)
                            .where(PatentPublication.id == patent_id)
                            .values(**values)
                        )

                        # Queue summarization if we got an abstract
                        if got_abstract:
                            from app.tasks.summarize import summarize_patent

                            summarize_patent.delay(str(patent_id), force=True)

                    except Exception:
                        stats["failed"] += 1
                        logger.exception("Failed to enrich %s via PatentsView", pub_number)

                    stats["processed"] += 1

                await session.commit()

            # Rate limit between chunks
            time.sleep(2.0)

    return stats
