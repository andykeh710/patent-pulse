"""
Focused enrichment + summarization for patents expiring in the next 6 months.

This is a one-shot script targeting the highest-ROI patents: those about to
enter the public domain. Runs sequentially to:
  1. Enrich each patent with abstract (EPO OPS), claims + description (Google Patents)
  2. Queue summarization for each successfully-enriched patent

Intended to be run from inside the worker container:
    docker compose exec worker python3 -m scripts.enrich_priority_6mo

LLM cost budget: ~$3 for ~134 patents at $0.021 per summary.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta

from sqlalchemy import select, update

from app.config import settings
from app.core.models import PatentPublication
from app.database import async_session_maker
from app.ingestion.epo_client import EPOClient
from app.ingestion.google_patents_client import GooglePatentsClient
from app.tasks.summarize import summarize_patent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Throttle between API calls — respect EPO/Google rate limits
THROTTLE = 0.5


async def select_priority_patents() -> list[tuple]:
    """Select granted patents expiring within 6 months that need enrichment."""
    six_months_out = datetime.utcnow().date() + timedelta(days=183)

    async with async_session_maker() as session:
        result = await session.execute(
            select(
                PatentPublication.id,
                PatentPublication.doc_id,
                PatentPublication.publication_number,
                PatentPublication.kind_code,
                PatentPublication.title,
                PatentPublication.estimated_expiry_date,
                PatentPublication.abstract,
                PatentPublication.claims_text,
                PatentPublication.description_text,
            )
            .where(PatentPublication.legal_status == "GRANTED")
            .where(PatentPublication.office == "USPTO")
            .where(PatentPublication.estimated_expiry_date >= datetime.utcnow().date())
            .where(PatentPublication.estimated_expiry_date <= six_months_out)
            .order_by(PatentPublication.estimated_expiry_date.asc())
        )
        return list(result.all())


async def enrich_one(session, epo_client, gp_client, patent) -> dict:
    """Enrich a single patent. Returns stats dict."""
    stats = {"abstract": False, "claims": False, "description": False, "from_cache": False}

    # Skip if already fully enriched
    if patent.abstract and patent.claims_text and patent.description_text:
        stats["from_cache"] = True
        return stats

    values: dict = {"updated_at": datetime.utcnow()}

    # Source 1: EPO OPS for abstract (if missing)
    if not patent.abstract or len(patent.abstract or "") <= 100:
        try:
            abstract = epo_client.fetch_abstract_for_us_patent(patent.publication_number)
            if abstract:
                values["abstract"] = abstract
                stats["abstract"] = True
        except Exception as e:
            logger.warning(f"EPO abstract fetch failed for {patent.doc_id}: {e}")
        time.sleep(THROTTLE)

    # Source 2: Google Patents for claims + description (and abstract fallback)
    need_claims = not patent.claims_text or len(patent.claims_text or "") <= 100
    need_desc = not patent.description_text or len(patent.description_text or "") <= 500
    need_abs_fallback = "abstract" not in values and (not patent.abstract or len(patent.abstract or "") <= 100)

    if need_claims or need_desc or need_abs_fallback:
        try:
            gp = gp_client.fetch_patent_fulltext(
                patent.publication_number, patent.kind_code or "B2"
            )
            if need_abs_fallback and gp.get("abstract"):
                values["abstract"] = gp["abstract"]
                stats["abstract"] = True
            if need_claims and gp.get("claims_text"):
                values["claims_text"] = gp["claims_text"]
                stats["claims"] = True
            if need_desc and gp.get("description_text"):
                values["description_text"] = gp["description_text"]
                stats["description"] = True
        except Exception as e:
            logger.warning(f"Google Patents fetch failed for {patent.doc_id}: {e}")
        time.sleep(THROTTLE)

    # Update only if we got something new
    if len(values) > 1:  # more than just updated_at
        await session.execute(
            update(PatentPublication)
            .where(PatentPublication.id == patent.id)
            .values(**values)
        )
        await session.commit()

    return stats


async def main() -> None:
    if not settings.epo_ops_client_id or not settings.epo_ops_client_secret:
        logger.error("EPO OPS credentials missing — aborting")
        return

    patents = await select_priority_patents()
    logger.info(f"Found {len(patents)} patents expiring in next 6 months")

    if not patents:
        logger.info("Nothing to do")
        return

    # Enrichment phase — sequential, respectful rate limiting
    totals = {"abstracts_added": 0, "claims_added": 0, "descriptions_added": 0, "skipped_cached": 0}
    queued_summaries: list[str] = []

    with EPOClient() as epo_client, GooglePatentsClient() as gp_client:
        async with async_session_maker() as session:
            for idx, patent in enumerate(patents, 1):
                logger.info(
                    f"[{idx}/{len(patents)}] {patent.doc_id} expires {patent.estimated_expiry_date} — "
                    f"{(patent.title or '')[:60]}"
                )
                stats = await enrich_one(session, epo_client, gp_client, patent)
                if stats["from_cache"]:
                    totals["skipped_cached"] += 1
                if stats["abstract"]:
                    totals["abstracts_added"] += 1
                if stats["claims"]:
                    totals["claims_added"] += 1
                if stats["description"]:
                    totals["descriptions_added"] += 1

                # Queue summarization if we have content (new or cached)
                has_abstract = stats["abstract"] or bool(patent.abstract and len(patent.abstract) > 100)
                if has_abstract:
                    queued_summaries.append(str(patent.id))

    logger.info(f"Enrichment complete: {totals}")

    # Summarization phase — queue via Celery (forces re-summarize with new abstract)
    logger.info(f"Queueing {len(queued_summaries)} summarization tasks (~${len(queued_summaries) * 0.021:.2f})")
    for pid in queued_summaries:
        summarize_patent.delay(pid, force=True)

    logger.info("All tasks queued. Monitor progress:")
    logger.info("  docker compose logs -f worker | grep summarize")


if __name__ == "__main__":
    asyncio.run(main())
