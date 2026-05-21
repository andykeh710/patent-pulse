"""
Convergence Signal computation.

Identifies pairs of CPC sections that appear together on patents at an
accelerating rate. A rising co-occurrence rate between two technology areas
signals industry convergence -- e.g. AI + Healthcare, or Energy + Materials.

Populates the ``convergence_signals`` table.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import ConvergenceSignal
from app.database import async_session_maker
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

RECENT_WINDOW_MONTHS = 6
BASELINE_WINDOW_MONTHS = 24
MIN_JOINT_COUNT = 3
MIN_BASELINE_COUNT = 2
CPC_PREFIX_LENGTH = 4


@celery_app.task(
    bind=True,
    name="app.tasks.compute_convergence.compute_convergence_signals",
    max_retries=2,
    default_retry_delay=120,
)
def compute_convergence_signals(self) -> dict[str, Any]:
    """Compute CPC pair convergence signals."""
    logger.info("Computing convergence signals")
    stats = asyncio.run(_compute_signals())
    logger.info("Convergence computation complete: %s", stats)
    return stats


async def _compute_signals() -> dict[str, Any]:
    today = date.today()
    recent_start = today - timedelta(days=RECENT_WINDOW_MONTHS * 30)
    baseline_start = today - timedelta(days=BASELINE_WINDOW_MONTHS * 30)
    baseline_end = recent_start

    async with async_session_maker() as session:
        recent_pairs = await _cpc_pair_counts(session, recent_start, today)
        baseline_pairs = await _cpc_pair_counts(session, baseline_start, baseline_end)

        signals = []
        ws = datetime.combine(recent_start, datetime.min.time())

        for (cpc_a, cpc_b), joint_count in recent_pairs.items():
            if joint_count < MIN_JOINT_COUNT:
                continue

            baseline_count = baseline_pairs.get((cpc_a, cpc_b), 0)
            if baseline_count < MIN_BASELINE_COUNT:
                recent_rate = joint_count / RECENT_WINDOW_MONTHS
                growth_ratio = recent_rate * 10 if joint_count >= MIN_JOINT_COUNT else 0
            else:
                recent_rate = joint_count / RECENT_WINDOW_MONTHS
                baseline_rate = baseline_count / (BASELINE_WINDOW_MONTHS - RECENT_WINDOW_MONTHS)
                growth_ratio = recent_rate / baseline_rate if baseline_rate > 0 else 0

            if growth_ratio <= 0.5:
                continue

            signals.append({
                "cpc_a": cpc_a,
                "cpc_b": cpc_b,
                "window_start": ws,
                "window_months": RECENT_WINDOW_MONTHS,
                "joint_count": joint_count,
                "baseline_count": baseline_count,
                "growth_ratio": round(growth_ratio, 4),
            })

        if signals:
            await _upsert_signals(session, signals)
            await session.commit()

        return {
            "recent_pairs_evaluated": len(recent_pairs),
            "signals_written": len(signals),
        }


async def _cpc_pair_counts(
    session: AsyncSession, start: date, end: date
) -> dict[tuple[str, str], int]:
    """Count co-occurrences of CPC prefix pairs on the same patent."""
    rows = await session.execute(text("""
        WITH patent_prefixes AS (
            SELECT p.id,
                   substr(c.val, 1, :plen) AS prefix
            FROM patent_publications p,
                 jsonb_array_elements_text(p.cpc) AS c(val)
            WHERE p.publication_date >= :start
              AND p.publication_date <= :end
              AND jsonb_array_length(p.cpc) > 1
            GROUP BY p.id, prefix
        )
        SELECT a.prefix AS cpc_a, b.prefix AS cpc_b,
               count(DISTINCT a.id) AS cnt
        FROM patent_prefixes a
        JOIN patent_prefixes b ON a.id = b.id AND a.prefix < b.prefix
        GROUP BY a.prefix, b.prefix
        HAVING count(DISTINCT a.id) >= :min_count
        ORDER BY cnt DESC
        LIMIT 500
    """), {
        "plen": CPC_PREFIX_LENGTH,
        "start": start,
        "end": end,
        "min_count": MIN_BASELINE_COUNT,
    })

    return {(r[0], r[1]): r[2] for r in rows}


async def _upsert_signals(
    session: AsyncSession, signals: list[dict[str, Any]]
) -> None:
    for sig in signals:
        stmt = pg_insert(ConvergenceSignal).values(**sig)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_convergence_pair_window",
            set_={
                "joint_count": stmt.excluded.joint_count,
                "baseline_count": stmt.excluded.baseline_count,
                "growth_ratio": stmt.excluded.growth_ratio,
            },
        )
        await session.execute(stmt)
