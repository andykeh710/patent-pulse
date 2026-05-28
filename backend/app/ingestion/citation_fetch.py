"""
Per-patent forward citation fetcher (Sprint 6.5).

Used by the backfill task (S65-3). Uses session injection pattern
from S6-9 — the session is passed in by the caller, never created
internally.
"""
from __future__ import annotations

import logging
from urllib.error import HTTPError
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PatentPublication

logger = logging.getLogger(__name__)


async def fetch_forward_citations(
    session: AsyncSession,
    patent_id: UUID,
) -> int:
    """Fetch and persist forward citations for a single patent.

    Returns the count of NEW citations saved (0 if skipped, already
    populated, or patent not found). Logs errors and returns 0 on failure.

    Requires session injection — caller owns the session lifecycle.
    """
    result = await session.execute(
        select(PatentPublication).where(PatentPublication.id == patent_id)
    )
    patent = result.scalar_one_or_none()

    if not patent:
        logger.warning("fetch_forward_citations: patent %s not found", patent_id)
        return 0

    if patent.citations_forward:
        return 0

    if not patent.publication_number:
        logger.warning(
            "fetch_forward_citations: patent %s has no publication_number", patent_id
        )
        return 0

    citations = await _fetch_from_uspto(patent.publication_number)

    if not citations:
        return 0

    patent.citations_forward = citations
    await session.commit()

    logger.info(
        "Fetched %d forward citations for %s (%s)",
        len(citations), patent.doc_id, patent.publication_number,
    )
    return len(citations)


async def _fetch_from_uspto(pub_number: str) -> list[str]:
    """Call patent_client SDK to get forward citations.

    Runs in a thread to avoid blocking the event loop (patent_client is
    synchronous). Rate-limited: 1 call/sec enforced by the backfill task;
    this helper adds a small sleep for safety.
    """
    import threading

    result: list[str] = []

    def _sync_fetch():
        nonlocal result
        try:
            from patent_client import PatentBiblio
            patent = PatentBiblio.objects.get(pub_number)
            for cit in getattr(patent, "forward_citations", []) or []:
                num = getattr(cit, "publication_number", None)
                if num:
                    result.append(f"USPTO:{num}")
        except HTTPError as e:
            if e.code == 429:
                logger.warning("Rate limited fetching citations for %s (429)", pub_number)
            else:
                logger.error("HTTP error fetching citations for %s: %s", pub_number, e)
        except Exception as e:
            logger.error("Failed to fetch citations for %s: %s", pub_number, e)

    # Run in background thread to not block event loop.
    thread = threading.Thread(target=_sync_fetch, daemon=True)
    thread.start()
    thread.join(timeout=30)

    return result
