"""
Trends API.

Surfaces aggregate trend data from ``trend_snapshots``, ``convergence_signals``,
and ``patent_cliff_clusters`` tables. Designed for the /trends frontend page.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, func, select

from app.api.deps import DbSession
from app.core.ai_models import ConvergenceSignal, PatentCliffCluster, TrendSnapshot

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TrendItem(BaseModel):
    surface: str
    key: str
    week_start: datetime
    count_4w: int
    count_12w: int
    baseline_12mo: float
    z_score: float
    growth_pct: float
    assignee_diversity: float
    cpc_diversity: float
    top_patent_ids: list[str]

    model_config = ConfigDict(from_attributes=True)


class TrendListResponse(BaseModel):
    items: list[TrendItem]
    total: int


class ConvergenceItem(BaseModel):
    cpc_a: str
    cpc_b: str
    joint_count: int
    baseline_count: int
    growth_ratio: float

    model_config = ConfigDict(from_attributes=True)


class CliffClusterItem(BaseModel):
    id: UUID
    key_type: str
    key_value: str
    window_months: int
    patent_count: int
    representative_patent_ids: list[str]

    model_config = ConfigDict(from_attributes=True)


class CliffListResponse(BaseModel):
    items: list[CliffClusterItem]
    total: int


class TrendsSummary(BaseModel):
    total_trend_rows: int
    surfaces: dict[str, int]
    convergence_signals: int
    cliff_clusters: int
    last_computed: datetime | None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=TrendsSummary)
async def trends_summary(db: DbSession) -> TrendsSummary:
    """High-level overview of available trend intelligence."""
    total = (await db.execute(
        select(func.count()).select_from(TrendSnapshot)
    )).scalar_one()

    surface_rows = (await db.execute(
        select(TrendSnapshot.surface, func.count())
        .group_by(TrendSnapshot.surface)
    )).all()
    surfaces = {r[0]: r[1] for r in surface_rows}

    conv_count = (await db.execute(
        select(func.count()).select_from(ConvergenceSignal)
    )).scalar_one()

    cliff_count = (await db.execute(
        select(func.count()).select_from(PatentCliffCluster)
    )).scalar_one()

    last = (await db.execute(
        select(func.max(TrendSnapshot.created_at))
    )).scalar_one()

    return TrendsSummary(
        total_trend_rows=total,
        surfaces=surfaces,
        convergence_signals=conv_count,
        cliff_clusters=cliff_count,
        last_computed=last,
    )


@router.get("/hot", response_model=TrendListResponse)
async def hot_trends(
    db: DbSession,
    surface: Literal["cpc", "tag", "assignee"] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> TrendListResponse:
    """Top trends ranked by z-score. Optionally filter by surface type."""
    stmt = select(TrendSnapshot).order_by(TrendSnapshot.z_score.desc())

    if surface:
        stmt = stmt.where(TrendSnapshot.surface == surface)

    stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    count_stmt = select(func.count()).select_from(TrendSnapshot)
    if surface:
        count_stmt = count_stmt.where(TrendSnapshot.surface == surface)
    total = (await db.execute(count_stmt)).scalar_one()

    return TrendListResponse(
        items=[TrendItem.model_validate(r) for r in rows],
        total=total,
    )


@router.get("/growing", response_model=TrendListResponse)
async def growing_trends(
    db: DbSession,
    surface: Literal["cpc", "tag", "assignee"] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> TrendListResponse:
    """Trends ranked by growth percentage (recent velocity vs baseline)."""
    stmt = select(TrendSnapshot).where(
        TrendSnapshot.count_4w >= 3
    ).order_by(TrendSnapshot.growth_pct.desc())

    if surface:
        stmt = stmt.where(TrendSnapshot.surface == surface)

    stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    return TrendListResponse(
        items=[TrendItem.model_validate(r) for r in rows],
        total=len(rows),
    )


@router.get("/convergence", response_model=list[ConvergenceItem])
async def convergence_signals(
    db: DbSession,
    min_growth_ratio: float = Query(default=1.5, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[ConvergenceItem]:
    """Technology convergence signals: CPC pairs with accelerating co-occurrence."""
    rows = (await db.execute(
        select(ConvergenceSignal)
        .where(ConvergenceSignal.growth_ratio >= min_growth_ratio)
        .order_by(ConvergenceSignal.growth_ratio.desc())
        .limit(limit)
    )).scalars().all()

    return [ConvergenceItem.model_validate(r) for r in rows]


@router.get("/cliffs", response_model=CliffListResponse)
async def patent_cliffs(
    db: DbSession,
    window_months: int | None = Query(default=None),
    min_patents: int = Query(default=5, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
) -> CliffListResponse:
    """Patent cliff clusters: groups of expiring patents by CPC area."""
    stmt = select(PatentCliffCluster).where(
        PatentCliffCluster.patent_count >= min_patents
    ).order_by(PatentCliffCluster.patent_count.desc())

    if window_months is not None:
        stmt = stmt.where(PatentCliffCluster.window_months == window_months)

    stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    count_stmt = select(func.count()).select_from(PatentCliffCluster).where(
        PatentCliffCluster.patent_count >= min_patents
    )
    if window_months is not None:
        count_stmt = count_stmt.where(PatentCliffCluster.window_months == window_months)
    total = (await db.execute(count_stmt)).scalar_one()

    return CliffListResponse(
        items=[CliffClusterItem.model_validate(r) for r in rows],
        total=total,
    )


@router.get("/detail/{surface}/{key}", response_model=TrendItem | None)
async def trend_detail(
    db: DbSession,
    surface: str,
    key: str,
) -> TrendItem | None:
    """Get the latest trend snapshot for a specific surface+key."""
    row = (await db.execute(
        select(TrendSnapshot)
        .where(and_(TrendSnapshot.surface == surface, TrendSnapshot.key == key))
        .order_by(TrendSnapshot.week_start.desc())
        .limit(1)
    )).scalar_one_or_none()

    if not row:
        return None
    return TrendItem.model_validate(row)
