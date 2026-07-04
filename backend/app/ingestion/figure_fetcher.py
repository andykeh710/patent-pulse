"""Figure fetch orchestrator — chains providers → converts → stores → records."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.models import PatentFigure, PatentPublication
from app.ingestion.figure_conversion import convert_figure
from app.ingestion.figure_storage import get_storage
from app.patent_sources.registry import get as get_provider

logger = logging.getLogger(__name__)

# Token-bucket rate limiters (simple in-process — adequate for single-worker)
_last_epo_call: float = 0.0
_last_odp_call: float = 0.0


def _rate_limit(source: str) -> None:
    """Block until rate limit window passes for the given source."""
    global _last_epo_call, _last_odp_call
    if source == "epo_ops":
        interval = 1.0 / max(settings.epo_ops_max_rps, 0.1)
        elapsed = time.monotonic() - _last_epo_call
        if elapsed < interval:
            time.sleep(interval - elapsed)
        _last_epo_call = time.monotonic()
    elif source == "uspto_odp":
        interval = 1.0 / max(settings.uspto_odp_max_rps, 0.1)
        elapsed = time.monotonic() - _last_odp_call
        if elapsed < interval:
            time.sleep(interval - elapsed)
        _last_odp_call = time.monotonic()


async def fetch_and_store_figures(
    session: AsyncSession,
    patent: PatentPublication,
) -> dict[str, Any]:
    """Fetch figures for a single patent, store them, return stats.

    Provider chain: EPO OPS → USPTO ODP (Google Patents behind feature flag).

    Failure NEVER raises — returns a result dict. The main ingestion
    pipeline must not be blocked by figure fetch failures.
    """
    pub_num = patent.publication_number or ""
    patent_id = str(patent.id)
    storage = get_storage()

    stats: dict[str, Any] = {
        "patent_id": patent_id,
        "publication_number": pub_num,
        "source": None,
        "fetched": 0,
        "stored": 0,
        "failed": 0,
        "status": "pending",
    }

    # ── Source chain ──────────────────────────────────────────────
    images: list[dict] = []

    # 1. USPTO (primary — 99% of corpus is US)
    try:
        from app.ingestion.uspto_figure_fetcher import fetch_uspto_figures

        _rate_limit("uspto_odp")
        images = fetch_uspto_figures(pub_num)
        if images:
            stats["source"] = "uspto_odp"
    except Exception:
        logger.debug("USPTO figure fetch failed for %s", pub_num, exc_info=True)

    # 2. EPO OPS (secondary — EP/WO patents)
    if not images:
        epo = get_provider("epo_ops")
        if epo:
            try:
                _rate_limit("epo_ops")
                images = epo.fetch_images(pub_num)
                if images:
                    stats["source"] = "epo_ops"
            except Exception:
                logger.debug("EPO OPS image fetch failed for %s", pub_num, exc_info=True)

    # 3. Google Patents (behind feature flag)
    if not images and settings.google_patents_images_enabled:
        logger.debug("Google Patents image fallback disabled (ToS gray area)")

    if not images:
        stats["status"] = "unavailable"
        await _update_figures_status(session, patent_id, "unavailable")
        return stats

    stats["fetched"] = len(images)

    # ── Convert + store ───────────────────────────────────────────
    stored_count = 0
    thumbnail_url: str | None = None

    for idx, img_meta in enumerate(images):
        raw_bytes = img_meta.get("raw_bytes")
        if not raw_bytes:
            stats["failed"] += 1
            continue

        ordinal = idx + 1
        try:
            converted = convert_figure(raw_bytes)
            if converted is None:
                stats["failed"] += 1
                continue

            full_path = storage.save(patent_id, ordinal, converted.full_bytes, "png")
            thumb_path = storage.save(patent_id, ordinal, converted.thumb_bytes, "png")

            figure = PatentFigure(
                patent_id=uuid.UUID(patent_id),
                ordinal=ordinal,
                source=stats["source"] or "unknown",
                width=converted.width,
                height=converted.height,
                full_path=full_path,
                thumb_path=thumb_path,
                mime_type="image/png",
                source_url=img_meta.get("source_url"),
                figure_label=img_meta.get("figure_label"),
            )
            session.add(figure)
            stored_count += 1

            if thumbnail_url is None:
                thumbnail_url = (
                    f"{settings.figures_serve_url_prefix}/{patent_id}/figures/1/thumbnail"
                )

        except Exception:
            logger.warning(
                "Figure %d conversion/storage failed for %s", ordinal, pub_num, exc_info=True
            )
            stats["failed"] += 1

    await session.flush()

    # ── Update patent record ──────────────────────────────────────
    stats["stored"] = stored_count
    if stored_count == stats["fetched"]:
        stats["status"] = "complete"
    elif stored_count > 0:
        stats["status"] = "partial"
    else:
        stats["status"] = "unavailable"

    await session.execute(
        update(PatentPublication)
        .where(PatentPublication.id == uuid.UUID(patent_id))
        .values(
            figures_status=stats["status"],
            thumbnail_url=thumbnail_url,
        )
    )

    return stats


async def _update_figures_status(session: AsyncSession, patent_id: str, status: str) -> None:
    await session.execute(
        update(PatentPublication)
        .where(PatentPublication.id == uuid.UUID(patent_id))
        .values(figures_status=status)
    )
