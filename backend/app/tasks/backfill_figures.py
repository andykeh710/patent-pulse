"""
Figure URL backfill task (Sprint 4.5).

Computes Google Patents thumbnails page URLs for patents that don't
yet have a figure_page_url. Link-out only — no scraping, no image hosting.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, update

from app.core.models import PatentPublication
from app.database import async_session_maker

logger = logging.getLogger(__name__)


def compute_figure_page_url(publication_number: str, office: str) -> str | None:
    """Compute the Google Patents thumbnails page URL.

    Format: https://patents.google.com/patent/{office_prefix}{pub_number}/thumbnails

    Returns None for design patents ('D' prefix) — Google Patents uses
    different routing for design patents that doesn't map cleanly to this
    URL pattern. Frontend renders empty state cleanly when URL is null.
    """
    # Design patents (e.g. D1127226) don't resolve with this URL pattern.
    stripped = publication_number.strip()
    if stripped.upper().startswith("D"):
        return None

    # Office prefix: first 2 letters of the office code.
    prefix = office[:2].upper() if office and len(office) >= 2 else "US"
    # Strip any leading office/country prefixes from the publication number.
    clean = stripped
    for pfx in ("US", "EP", "WO", "JP", "CN", "KR", "GB", "DE", "FR", "CA", "AU"):
        if clean.upper().startswith(pfx):
            clean = clean[len(pfx):]
            break
    return f"https://patents.google.com/patent/{prefix}{clean}/thumbnails"


async def backfill_figure_urls(
    *,
    limit: int | None = 5000,
    offset: int = 0,
) -> dict[str, Any]:
    """Backfill figure_page_url for patents missing it.

    Returns dict with keys: total_processed, updated, skipped.
    Idempotent — only updates patents with NULL figure_page_url.
    """
    stats: dict[str, int] = {"total_processed": 0, "updated": 0, "skipped": 0}

    async with async_session_maker() as session:
        # Fetch IDs + publication_number + office for patents missing URL.
        result = await session.execute(
            select(
                PatentPublication.id,
                PatentPublication.publication_number,
                PatentPublication.office,
            )
            .where(PatentPublication.figure_page_url.is_(None))
            .where(PatentPublication.publication_number.isnot(None))
            .order_by(PatentPublication.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = result.all()

        for row in rows:
            patent_id, pub_number, office = row
            url = compute_figure_page_url(pub_number, office)
            await session.execute(
                update(PatentPublication)
                .where(PatentPublication.id == patent_id)
                .values(figure_page_url=url)
            )
            stats["updated"] += 1

        await session.commit()
        stats["total_processed"] = len(rows)
        logger.info(
            "Figure URL backfill: processed=%d updated=%d",
            len(rows),
            stats["updated"],
        )
        return stats


async def backfill_figure_urls_for_session(
    session,
    *,
    limit: int | None = 5000,
    offset: int = 0,
) -> dict[str, Any]:
    """Session-aware variant (testable)."""
    stats: dict[str, int] = {"total_processed": 0, "updated": 0, "skipped": 0}

    result = await session.execute(
        select(
            PatentPublication.id,
            PatentPublication.publication_number,
            PatentPublication.office,
        )
        .where(PatentPublication.figure_page_url.is_(None))
        .where(PatentPublication.publication_number.isnot(None))
        .order_by(PatentPublication.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()

    for row in rows:
        patent_id, pub_number, office = row
        url = compute_figure_page_url(pub_number, office)
        await session.execute(
            update(PatentPublication)
            .where(PatentPublication.id == patent_id)
            .values(figure_page_url=url)
        )
        stats["updated"] += 1

    await session.commit()
    stats["total_processed"] = len(rows)
    return stats
