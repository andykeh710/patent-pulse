"""
Weekly aggregate trend computation.

Populates the ``trend_snapshots`` table with per-surface (cpc, tag, theme,
assignee) weekly statistics: 4-week and 12-week patent counts, 12-month
baseline, z-score, growth percentage, and diversity metrics.

Designed to run weekly after ingestion completes (Sunday schedule).
"""
from __future__ import annotations

import asyncio
import logging
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import TrendSnapshot
from app.database import async_session_maker
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

WEEK_DAYS = 7
FOUR_WEEKS = 28
TWELVE_WEEKS = 84
TWELVE_MONTHS_DAYS = 365
MIN_BASELINE_COUNT = 3
TOP_PATENTS_PER_TREND = 5
MIN_CPC_PREFIX_LENGTH = 4


def _monday_of_week(d: date) -> date:
    """Return the Monday of the ISO week containing ``d``."""
    return d - timedelta(days=d.weekday())


@celery_app.task(
    bind=True,
    name="app.tasks.compute_trends.compute_weekly_trends",
    max_retries=2,
    default_retry_delay=120,
)
def compute_weekly_trends(self, reference_date: str | None = None) -> dict[str, Any]:
    """
    Compute trend snapshots for the current week.

    Args:
        reference_date: ISO date string. Defaults to today.
    """
    ref = date.fromisoformat(reference_date) if reference_date else date.today()
    week_start = _monday_of_week(ref)
    logger.info("Computing weekly trends for week starting %s", week_start)
    stats = asyncio.run(_compute_all_surfaces(week_start))
    logger.info("Trend computation complete: %s", stats)
    return stats


async def _compute_all_surfaces(week_start: date) -> dict[str, Any]:
    """Compute trends for all surfaces and upsert into trend_snapshots."""
    stats: dict[str, int] = {}

    async with async_session_maker() as session:
        cpc_rows = await _compute_cpc_trends(session, week_start)
        stats["cpc"] = len(cpc_rows)

        tag_rows = await _compute_tag_trends(session, week_start)
        stats["tag"] = len(tag_rows)

        assignee_rows = await _compute_assignee_trends(session, week_start)
        stats["assignee"] = len(assignee_rows)

        all_rows = cpc_rows + tag_rows + assignee_rows
        if all_rows:
            await _upsert_snapshots(session, all_rows)
            await session.commit()

        stats["total"] = len(all_rows)

    return stats


async def _compute_cpc_trends(
    session: AsyncSession, week_start: date
) -> list[dict[str, Any]]:
    """Compute trends for CPC 4-char prefixes (e.g. G06F, A61B)."""
    today = week_start + timedelta(days=6)
    four_weeks_ago = today - timedelta(days=FOUR_WEEKS)
    twelve_weeks_ago = today - timedelta(days=TWELVE_WEEKS)
    twelve_months_ago = today - timedelta(days=TWELVE_MONTHS_DAYS)

    rows_4w = await session.execute(text("""
        SELECT substr(c.val, 1, :plen) AS prefix,
               count(DISTINCT p.id) AS cnt,
               count(DISTINCT p.assignees->0) AS assignee_cnt
        FROM patent_publications p,
             jsonb_array_elements_text(p.cpc) AS c(val)
        WHERE p.publication_date >= :start AND p.publication_date <= :end
          AND jsonb_array_length(p.cpc) > 0
        GROUP BY prefix
        HAVING count(DISTINCT p.id) >= 1
    """), {"plen": MIN_CPC_PREFIX_LENGTH, "start": four_weeks_ago, "end": today})
    counts_4w = {r[0]: (r[1], r[2]) for r in rows_4w}

    rows_12w = await session.execute(text("""
        SELECT substr(c.val, 1, :plen) AS prefix,
               count(DISTINCT p.id) AS cnt
        FROM patent_publications p,
             jsonb_array_elements_text(p.cpc) AS c(val)
        WHERE p.publication_date >= :start AND p.publication_date <= :end
          AND jsonb_array_length(p.cpc) > 0
        GROUP BY prefix
    """), {"plen": MIN_CPC_PREFIX_LENGTH, "start": twelve_weeks_ago, "end": today})
    counts_12w = {r[0]: r[1] for r in rows_12w}

    rows_12mo = await session.execute(text("""
        SELECT substr(c.val, 1, :plen) AS prefix,
               count(DISTINCT p.id) AS cnt
        FROM patent_publications p,
             jsonb_array_elements_text(p.cpc) AS c(val)
        WHERE p.publication_date >= :start AND p.publication_date <= :end
          AND jsonb_array_length(p.cpc) > 0
        GROUP BY prefix
    """), {"plen": MIN_CPC_PREFIX_LENGTH, "start": twelve_months_ago, "end": today})
    counts_12mo = {r[0]: r[1] for r in rows_12mo}

    top_patents = await _top_patents_by_cpc(session, four_weeks_ago, today)

    results = []
    all_prefixes = set(counts_4w) | set(counts_12w)
    for prefix in all_prefixes:
        c4 = counts_4w.get(prefix, (0, 0))
        c12 = counts_12w.get(prefix, 0)
        c12mo = counts_12mo.get(prefix, 0)
        weekly_avg_12mo = c12mo / (TWELVE_MONTHS_DAYS / WEEK_DAYS) if c12mo else 0
        weekly_count_4w = c4[0] / (FOUR_WEEKS / WEEK_DAYS)

        z = _z_score(weekly_count_4w, weekly_avg_12mo, c12mo)
        growth = _growth_pct(c4[0], c12, FOUR_WEEKS, TWELVE_WEEKS)

        results.append({
            "surface": "cpc",
            "key": prefix,
            "week_start": datetime.combine(week_start, datetime.min.time()),
            "count_4w": c4[0],
            "count_12w": c12,
            "baseline_12mo": round(weekly_avg_12mo, 4),
            "z_score": round(z, 4),
            "growth_pct": round(growth, 4),
            "assignee_diversity": _diversity_ratio(c4[1], c4[0]),
            "cpc_diversity": 0.0,
            "top_patent_ids": top_patents.get(prefix, [])[:TOP_PATENTS_PER_TREND],
        })

    return results


async def _compute_tag_trends(
    session: AsyncSession, week_start: date
) -> list[dict[str, Any]]:
    """Compute trends for trend_tags from patent tags."""
    today = week_start + timedelta(days=6)
    four_weeks_ago = today - timedelta(days=FOUR_WEEKS)
    twelve_weeks_ago = today - timedelta(days=TWELVE_WEEKS)
    twelve_months_ago = today - timedelta(days=TWELVE_MONTHS_DAYS)

    def _tag_query(start: date, end: date) -> text:
        return text("""
            SELECT t.val AS tag, count(DISTINCT p.id) AS cnt
            FROM patent_publications p,
                 jsonb_array_elements_text(p.tags->'trend_tags') AS t(val)
            WHERE p.publication_date >= :start AND p.publication_date <= :end
              AND p.tags IS NOT NULL
              AND p.tags->'trend_tags' IS NOT NULL
            GROUP BY tag
        """)

    rows_4w = await session.execute(_tag_query(four_weeks_ago, today),
                                     {"start": four_weeks_ago, "end": today})
    counts_4w = {r[0]: r[1] for r in rows_4w}

    rows_12w = await session.execute(_tag_query(twelve_weeks_ago, today),
                                      {"start": twelve_weeks_ago, "end": today})
    counts_12w = {r[0]: r[1] for r in rows_12w}

    rows_12mo = await session.execute(_tag_query(twelve_months_ago, today),
                                       {"start": twelve_months_ago, "end": today})
    counts_12mo = {r[0]: r[1] for r in rows_12mo}

    results = []
    for tag in set(counts_4w) | set(counts_12w):
        c4 = counts_4w.get(tag, 0)
        c12 = counts_12w.get(tag, 0)
        c12mo = counts_12mo.get(tag, 0)
        weekly_avg = c12mo / (TWELVE_MONTHS_DAYS / WEEK_DAYS) if c12mo else 0
        weekly_4w = c4 / (FOUR_WEEKS / WEEK_DAYS)

        results.append({
            "surface": "tag",
            "key": tag,
            "week_start": datetime.combine(week_start, datetime.min.time()),
            "count_4w": c4,
            "count_12w": c12,
            "baseline_12mo": round(weekly_avg, 4),
            "z_score": round(_z_score(weekly_4w, weekly_avg, c12mo), 4),
            "growth_pct": round(_growth_pct(c4, c12, FOUR_WEEKS, TWELVE_WEEKS), 4),
            "assignee_diversity": 0.0,
            "cpc_diversity": 0.0,
            "top_patent_ids": [],
        })

    return results


async def _compute_assignee_trends(
    session: AsyncSession, week_start: date
) -> list[dict[str, Any]]:
    """Compute trends for top assignees."""
    today = week_start + timedelta(days=6)
    four_weeks_ago = today - timedelta(days=FOUR_WEEKS)
    twelve_weeks_ago = today - timedelta(days=TWELVE_WEEKS)
    twelve_months_ago = today - timedelta(days=TWELVE_MONTHS_DAYS)

    def _assignee_query(start: date, end: date) -> text:
        return text("""
            SELECT a.val AS assignee, count(DISTINCT p.id) AS cnt,
                   count(DISTINCT substr(c.val, 1, 4)) AS cpc_cnt
            FROM patent_publications p,
                 jsonb_array_elements_text(p.assignees) AS a(val)
                 LEFT JOIN LATERAL jsonb_array_elements_text(p.cpc) AS c(val) ON true
            WHERE p.publication_date >= :start AND p.publication_date <= :end
            GROUP BY assignee
            HAVING count(DISTINCT p.id) >= 2
        """)

    rows_4w = await session.execute(_assignee_query(four_weeks_ago, today),
                                     {"start": four_weeks_ago, "end": today})
    data_4w = {r[0]: (r[1], r[2]) for r in rows_4w}

    rows_12w = await session.execute(text("""
        SELECT a.val AS assignee, count(DISTINCT p.id) AS cnt
        FROM patent_publications p,
             jsonb_array_elements_text(p.assignees) AS a(val)
        WHERE p.publication_date >= :start AND p.publication_date <= :end
        GROUP BY assignee
        HAVING count(DISTINCT p.id) >= 2
    """), {"start": twelve_weeks_ago, "end": today})
    counts_12w = {r[0]: r[1] for r in rows_12w}

    rows_12mo = await session.execute(text("""
        SELECT a.val AS assignee, count(DISTINCT p.id) AS cnt
        FROM patent_publications p,
             jsonb_array_elements_text(p.assignees) AS a(val)
        WHERE p.publication_date >= :start AND p.publication_date <= :end
        GROUP BY assignee
        HAVING count(DISTINCT p.id) >= 2
    """), {"start": twelve_months_ago, "end": today})
    counts_12mo = {r[0]: r[1] for r in rows_12mo}

    results = []
    for assignee in set(data_4w) | set(counts_12w):
        d4 = data_4w.get(assignee, (0, 0))
        c12 = counts_12w.get(assignee, 0)
        c12mo = counts_12mo.get(assignee, 0)
        weekly_avg = c12mo / (TWELVE_MONTHS_DAYS / WEEK_DAYS) if c12mo else 0
        weekly_4w = d4[0] / (FOUR_WEEKS / WEEK_DAYS)

        results.append({
            "surface": "assignee",
            "key": assignee,
            "week_start": datetime.combine(week_start, datetime.min.time()),
            "count_4w": d4[0],
            "count_12w": c12,
            "baseline_12mo": round(weekly_avg, 4),
            "z_score": round(_z_score(weekly_4w, weekly_avg, c12mo), 4),
            "growth_pct": round(_growth_pct(d4[0], c12, FOUR_WEEKS, TWELVE_WEEKS), 4),
            "assignee_diversity": 0.0,
            "cpc_diversity": _diversity_ratio(d4[1], d4[0]),
            "top_patent_ids": [],
        })

    return results


async def _top_patents_by_cpc(
    session: AsyncSession, start: date, end: date
) -> dict[str, list[str]]:
    """Return top patent IDs per CPC prefix in the date window."""
    rows = await session.execute(text("""
        SELECT substr(c.val, 1, :plen) AS prefix,
               p.id::text AS pid,
               COALESCE(p.interesting_score, 0) AS score
        FROM patent_publications p,
             jsonb_array_elements_text(p.cpc) AS c(val)
        WHERE p.publication_date >= :start AND p.publication_date <= :end
          AND jsonb_array_length(p.cpc) > 0
        ORDER BY prefix, score DESC
    """), {"plen": MIN_CPC_PREFIX_LENGTH, "start": start, "end": end})

    by_prefix: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        if len(by_prefix[r[0]]) < TOP_PATENTS_PER_TREND:
            by_prefix[r[0]].append(r[1])
    return dict(by_prefix)


async def _upsert_snapshots(
    session: AsyncSession, rows: list[dict[str, Any]]
) -> None:
    """Upsert trend snapshot rows using ON CONFLICT."""
    for row in rows:
        stmt = pg_insert(TrendSnapshot).values(**row)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_trend_surface_key_week",
            set_={
                "count_4w": stmt.excluded.count_4w,
                "count_12w": stmt.excluded.count_12w,
                "baseline_12mo": stmt.excluded.baseline_12mo,
                "z_score": stmt.excluded.z_score,
                "growth_pct": stmt.excluded.growth_pct,
                "assignee_diversity": stmt.excluded.assignee_diversity,
                "cpc_diversity": stmt.excluded.cpc_diversity,
                "top_patent_ids": stmt.excluded.top_patent_ids,
            },
        )
        await session.execute(stmt)


def _z_score(recent_weekly: float, baseline_weekly: float, total_12mo: int) -> float:
    """Compute a z-score for the recent activity vs 12-month baseline.

    Uses a Poisson-like approximation: std_dev ~ sqrt(baseline_weekly).
    Returns 0 when insufficient data.
    """
    if total_12mo < MIN_BASELINE_COUNT or baseline_weekly <= 0:
        return 0.0
    std = math.sqrt(baseline_weekly)
    if std < 0.01:
        return 0.0
    return (recent_weekly - baseline_weekly) / std


def _growth_pct(
    count_short: int, count_long: int,
    days_short: int, days_long: int,
) -> float:
    """Compute growth percentage: short-window rate vs long-window rate."""
    if count_long == 0 or days_long == 0:
        return 0.0
    rate_short = count_short / days_short
    rate_long = count_long / days_long
    if rate_long < 0.001:
        return 0.0
    return ((rate_short - rate_long) / rate_long) * 100.0


def _diversity_ratio(unique_count: int, total_count: int) -> float:
    """Ratio of unique entities to total patents in a window. 0..1."""
    if total_count == 0:
        return 0.0
    return round(min(unique_count / total_count, 1.0), 4)
