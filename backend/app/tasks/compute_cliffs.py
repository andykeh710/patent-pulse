"""
Patent Cliff Cluster computation.

Groups expiring patents by CPC prefix into ``patent_cliff_clusters`` rows
for multiple time windows (6, 12, 24, 60 months). A "cliff" is a window
where multiple related patents expire, creating an opportunity opening.

Designed to run weekly alongside trend computation.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import PatentCliffCluster
from app.database import async_session_maker
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

WINDOW_MONTHS = [6, 12, 24, 60]
MIN_CLUSTER_SIZE = 2
MAX_REPRESENTATIVE_PATENTS = 10
MIN_CPC_PREFIX_LENGTH = 4


@celery_app.task(
    bind=True,
    name="app.tasks.compute_cliffs.compute_cliff_clusters",
    max_retries=2,
    default_retry_delay=120,
)
def compute_cliff_clusters(self) -> dict[str, Any]:
    """Compute patent cliff clusters for all time windows."""
    logger.info("Computing patent cliff clusters")
    stats = asyncio.run(_compute_all_windows())
    logger.info("Cliff cluster computation complete: %s", stats)
    return stats


async def _compute_all_windows() -> dict[str, Any]:
    """Compute CPC-based cliff clusters for each time window."""
    today = date.today()
    stats: dict[str, int] = {}
    total = 0

    async with async_session_maker() as session:
        for months in WINDOW_MONTHS:
            window_end = today + timedelta(days=months * 30)
            clusters = await _compute_cpc_clusters(session, today, window_end, months)
            stats[f"{months}mo"] = len(clusters)
            total += len(clusters)

            if clusters:
                await _upsert_clusters(session, clusters)

        await session.commit()

    stats["total"] = total
    return stats


async def _compute_cpc_clusters(
    session: AsyncSession,
    window_start: date,
    window_end: date,
    window_months: int,
) -> list[dict[str, Any]]:
    """Find CPC prefixes with multiple patents expiring in the window."""
    rows = await session.execute(
        text("""
        SELECT substr(c.val, 1, :plen) AS prefix,
               count(DISTINCT p.id) AS cnt,
               array_agg(DISTINCT p.id::text ORDER BY p.id::text) AS patent_ids
        FROM patent_publications p,
             jsonb_array_elements_text(p.cpc) AS c(val)
        WHERE p.estimated_expiry_date >= :start
          AND p.estimated_expiry_date < :end
          AND p.legal_status IN ('GRANTED', 'EXPIRED')
          AND jsonb_array_length(p.cpc) > 0
        GROUP BY prefix
        HAVING count(DISTINCT p.id) >= :min_size
        ORDER BY cnt DESC
    """),
        {
            "plen": MIN_CPC_PREFIX_LENGTH,
            "start": window_start,
            "end": window_end,
            "min_size": MIN_CLUSTER_SIZE,
        },
    )

    clusters = []
    ws = datetime.combine(window_start, datetime.min.time())
    for r in rows:
        prefix, count, patent_ids = r[0], r[1], r[2]
        clusters.append(
            {
                "key_type": "cpc",
                "key_value": prefix,
                "window_months": window_months,
                "window_start": ws,
                "patent_count": count,
                "representative_patent_ids": patent_ids[:MAX_REPRESENTATIVE_PATENTS],
            }
        )

    return clusters


async def _upsert_clusters(session: AsyncSession, clusters: list[dict[str, Any]]) -> None:
    """Insert or update cliff cluster rows.

    We delete existing clusters for the same (key_type, key_value,
    window_months) before inserting, since there's no unique constraint
    on this combination in the model.
    """
    seen = set()
    for cluster in clusters:
        key = (cluster["key_type"], cluster["key_value"], cluster["window_months"])
        if key not in seen:
            await session.execute(
                PatentCliffCluster.__table__.delete().where(
                    and_(
                        PatentCliffCluster.key_type == cluster["key_type"],
                        PatentCliffCluster.key_value == cluster["key_value"],
                        PatentCliffCluster.window_months == cluster["window_months"],
                    )
                )
            )
            seen.add(key)

        session.add(PatentCliffCluster(**cluster))
