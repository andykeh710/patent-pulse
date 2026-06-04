"""
BigQuery targeted backfill for high-priority patent abstracts.

Queries the Google Patents public dataset (patents-public-data.patents.publications)
for patents that are high-priority but missing abstracts. Runs daily at 04:30 UTC.

Hard budget: maximum_bytes_billed=50GB per call.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import update

from app.config import settings
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# As of June 2026: ~35% of our 64K patents are high-priority and missing abstracts.
# BigQuery charges $6.25/TB scanned. 50GB cap = ~$0.31 per run max.
MAX_BYTES_BILLED = 50_000_000_000


@celery_app.task(
    bind=True,
    name="app.tasks.enrich_abstracts.backfill_high_priority_bigquery",
    max_retries=2,
    default_retry_delay=600,
)
def backfill_high_priority_bigquery(self, limit: int = 500) -> dict:
    """Fetch abstracts from BigQuery for high-priority patents.

    High priority = expiring within 18 months OR opportunity_score in top 5%
    OR in any user topic. Updates abstract and abstract_source='bigquery'.
    """
    if not settings.google_cloud_project:
        logger.warning("BigQuery not configured — skipping")
        return {"skipped": True, "reason": "GCP not configured"}

    logger.info("Starting BigQuery high-priority backfill (limit=%d)", limit)
    stats = asyncio.run(_bigquery_backfill_async(limit))
    logger.info("BigQuery backfill complete: %s", stats)
    return stats


async def _bigquery_backfill_async(limit: int) -> dict:
    from google.cloud import bigquery

    stats = {"processed": 0, "abstracts_added": 0, "not_found": 0, "failed": 0}

    # Step 1: Get high-priority patent numbers missing abstracts
    async with async_session_maker() as session:
        from sqlalchemy import text

        # Prioritize: expiring soonest ∪ top opportunity score
        rows = await session.execute(
            text(
                """
                WITH high_priority AS (
                    SELECT publication_number, id
                    FROM patent_publications
                    WHERE abstract IS NULL
                      AND (
                        estimated_expiry_date < NOW() + INTERVAL '18 months'
                        OR opportunity_score >= (
                            SELECT percentile_disc(0.95) WITHIN GROUP (ORDER BY opportunity_score)
                            FROM patent_publications
                            WHERE opportunity_score IS NOT NULL
                        )
                      )
                    ORDER BY
                        CASE WHEN estimated_expiry_date IS NOT NULL
                             THEN estimated_expiry_date
                             ELSE '2099-12-31' END ASC,
                        opportunity_score DESC NULLS LAST
                    LIMIT :limit
                )
                SELECT publication_number, id FROM high_priority
                """
            ),
            {"limit": limit},
        )
        targets = [(r[0], r[1]) for r in rows.all()]

    if not targets:
        logger.info("No high-priority patents need BigQuery backfill")
        return stats

    pub_numbers = [t[0] for t in targets]
    logger.info("BigQuery backfill: %d high-priority targets", len(pub_numbers))

    # Step 2: Query BigQuery for abstracts
    client = bigquery.Client(project=settings.google_cloud_project)
    job_config = bigquery.QueryJobConfig(maximum_bytes_billed=MAX_BYTES_BILLED)

    # Build query with explicit publication number list
    numbers_sql = ", ".join(f"'{pn}'" for pn in pub_numbers)
    query = f"""
        SELECT publication_number, abstract_localized
        FROM `patents-public-data.patents.publications`
        WHERE publication_number IN ({numbers_sql})
          AND abstract_localized IS NOT NULL
          AND abstract_localized != ''
    """

    bq_results: dict[str, str] = {}
    try:
        job = client.query(query, job_config=job_config)
        for row in job.result():
            bq_results[row.publication_number] = row.abstract_localized
        logger.info(
            "BigQuery returned %d abstracts (%.1f GB processed)",
            len(bq_results),
            (job.total_bytes_processed or 0) / 1e9,
        )
    except Exception as e:
        logger.exception("BigQuery query failed")
        return {"failed": True, "error": str(e)[:500]}

    # Step 3: Update patents with BigQuery abstracts
    updated_count = 0
    async with async_session_maker() as session:
        for pub_number, patent_id in targets:
            abstract = bq_results.get(pub_number)
            if not abstract:
                stats["not_found"] += 1
                stats["processed"] += 1
                continue

            await session.execute(
                update(PatentPublication)
                .where(PatentPublication.id == patent_id)
                .values(
                    abstract=abstract,
                    abstract_source="bigquery",
                    updated_at=datetime.now(timezone.utc),
                )
            )
            updated_count += 1
            stats["abstracts_added"] += 1
            stats["processed"] += 1

            # Queue summarization
            from app.tasks.summarize import summarize_patent
            summarize_patent.delay(str(patent_id), force=True)

        await session.commit()

    logger.info("BigQuery backfill: %d patents updated with abstracts", updated_count)
    return stats
