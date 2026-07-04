"""
Trends API.

Surfaces aggregate trend data from ``trend_snapshots``, ``convergence_signals``,
and ``patent_cliff_clusters`` tables. Designed for the /trends frontend page.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
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
    total = (await db.execute(select(func.count()).select_from(TrendSnapshot))).scalar_one()

    surface_rows = (
        await db.execute(
            select(TrendSnapshot.surface, func.count()).group_by(TrendSnapshot.surface)
        )
    ).all()
    surfaces = {r[0]: r[1] for r in surface_rows}

    conv_count = (
        await db.execute(select(func.count()).select_from(ConvergenceSignal))
    ).scalar_one()

    cliff_count = (
        await db.execute(select(func.count()).select_from(PatentCliffCluster))
    ).scalar_one()

    last = (await db.execute(select(func.max(TrendSnapshot.created_at)))).scalar_one()

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
    stmt = (
        select(TrendSnapshot)
        .where(TrendSnapshot.count_4w >= 3)
        .order_by(TrendSnapshot.growth_pct.desc())
    )

    if surface:
        stmt = stmt.where(TrendSnapshot.surface == surface)

    stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    count_stmt = select(func.count()).select_from(TrendSnapshot).where(TrendSnapshot.count_4w >= 3)
    if surface:
        count_stmt = count_stmt.where(TrendSnapshot.surface == surface)
    total = (await db.execute(count_stmt)).scalar_one()

    return TrendListResponse(
        items=[TrendItem.model_validate(r) for r in rows],
        total=total,
    )


@router.get("/convergence", response_model=list[ConvergenceItem])
async def convergence_signals(
    db: DbSession,
    min_growth_ratio: float = Query(default=1.5, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[ConvergenceItem]:
    """Technology convergence signals: CPC pairs with accelerating co-occurrence."""
    rows = (
        (
            await db.execute(
                select(ConvergenceSignal)
                .where(ConvergenceSignal.growth_ratio >= min_growth_ratio)
                .order_by(ConvergenceSignal.growth_ratio.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    return [ConvergenceItem.model_validate(r) for r in rows]


@router.get("/cliffs", response_model=CliffListResponse)
async def patent_cliffs(
    db: DbSession,
    window_months: int | None = Query(default=None),
    min_patents: int = Query(default=5, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
) -> CliffListResponse:
    """Patent cliff clusters: groups of expiring patents by CPC area."""
    stmt = (
        select(PatentCliffCluster)
        .where(PatentCliffCluster.patent_count >= min_patents)
        .order_by(PatentCliffCluster.patent_count.desc())
    )

    if window_months is not None:
        stmt = stmt.where(PatentCliffCluster.window_months == window_months)

    stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    count_stmt = (
        select(func.count())
        .select_from(PatentCliffCluster)
        .where(PatentCliffCluster.patent_count >= min_patents)
    )
    if window_months is not None:
        count_stmt = count_stmt.where(PatentCliffCluster.window_months == window_months)
    total = (await db.execute(count_stmt)).scalar_one()

    return CliffListResponse(
        items=[CliffClusterItem.model_validate(r) for r in rows],
        total=total,
    )


@router.get("/detail/{surface}/{key}", response_model=TrendItem)
async def trend_detail(
    db: DbSession,
    surface: str,
    key: str,
) -> TrendItem:
    """Get the latest trend snapshot for a specific surface+key."""
    row = (
        await db.execute(
            select(TrendSnapshot)
            .where(and_(TrendSnapshot.surface == surface, TrendSnapshot.key == key))
            .order_by(TrendSnapshot.week_start.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail=f"Trend not found for {surface}/{key}")
    return TrendItem.model_validate(row)


# ---------------------------------------------------------------------------
# Sprint 4 — Drilldown endpoints
# ---------------------------------------------------------------------------


class TrendDrilldownPatentsResponse(BaseModel):
    items: list
    total: int


class TrendAssigneeItem(BaseModel):
    assignee: str
    count: int


class TrendDrilldownAssigneesResponse(BaseModel):
    items: list[TrendAssigneeItem]
    total: int


class TrendNarrativeResponse(BaseModel):
    summary: str
    why_now: str
    key_assignees: list[str]
    related_trends: list[str]
    caveats: list[str]


# ── helper ────────────────────────────────────────────────────────────


async def _get_latest_trend_snapshot(db: DbSession, surface: str, key: str) -> TrendSnapshot:
    """Fetch the latest TrendSnapshot for a surface+key, or 404."""
    row = await db.execute(
        select(TrendSnapshot)
        .where(and_(TrendSnapshot.surface == surface, TrendSnapshot.key == key))
        .order_by(TrendSnapshot.week_start.desc())
        .limit(1)
    )
    trend = row.scalar_one_or_none()
    if not trend:
        raise HTTPException(
            status_code=404,
            detail=f"Trend not found for {surface}/{key}",
        )
    return trend


# ── patents driving this trend ────────────────────────────────────────


@router.get(
    "/{surface}/{key}/patents",
    response_model=TrendDrilldownPatentsResponse,
)
async def trend_patents(
    db: DbSession,
    surface: str,
    key: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> TrendDrilldownPatentsResponse:
    """Return patents driving a specific trend."""
    trend = await _get_latest_trend_snapshot(db, surface, key)
    patent_ids = trend.top_patent_ids or []

    if not patent_ids:
        return TrendDrilldownPatentsResponse(items=[], total=0)

    from uuid import UUID

    from app.core.models import PatentPublication
    from app.core.schemas import PatentListItem

    uuids = [UUID(pid) for pid in patent_ids]
    offset = (page - 1) * page_size

    result = await db.execute(
        select(PatentPublication)
        .where(PatentPublication.id.in_(uuids[:1000]))
        .offset(offset)
        .limit(page_size)
    )
    patents = result.scalars().all()
    items = [PatentListItem.from_patent(p) for p in patents]

    return TrendDrilldownPatentsResponse(
        items=items,
        total=min(len(patent_ids), 1000),
    )


# ── top assignees in this trend ───────────────────────────────────────


@router.get(
    "/{surface}/{key}/assignees",
    response_model=TrendDrilldownAssigneesResponse,
)
async def trend_assignees(
    db: DbSession,
    surface: str,
    key: str,
) -> TrendDrilldownAssigneesResponse:
    """Return assignees ranked by patent count in this trend."""
    trend = await _get_latest_trend_snapshot(db, surface, key)
    patent_ids = trend.top_patent_ids or []

    if not patent_ids:
        return TrendDrilldownAssigneesResponse(items=[], total=0)

    from uuid import UUID

    from app.core.models import PatentPublication

    uuids = [UUID(pid) for pid in patent_ids[:500]]
    result = await db.execute(
        select(PatentPublication.assignees).where(PatentPublication.id.in_(uuids))
    )
    rows = result.all()

    # Aggregate assignee counts.
    counter: dict[str, int] = {}
    for (assignees,) in rows:
        for name in assignees or []:
            counter[name] = counter.get(name, 0) + 1

    sorted_assignees = sorted(counter.items(), key=lambda x: x[1], reverse=True)
    items = [TrendAssigneeItem(assignee=name, count=count) for name, count in sorted_assignees[:20]]

    return TrendDrilldownAssigneesResponse(
        items=items,
        total=len(items),
    )


# ── trend narrative (AI-generated, cache-first) ───────────────────────


@router.get(
    "/{surface}/{key}/narrative",
    response_model=TrendNarrativeResponse | None,
)
async def get_trend_narrative(
    db: DbSession,
    surface: str,
    key: str,
) -> TrendNarrativeResponse | None:
    """Return cached trend narrative, or None if not yet generated."""
    from app.core.ai_models import AIArtifact

    result = await db.execute(
        select(AIArtifact)
        .where(
            AIArtifact.artifact_type == "trend_narrative",
            AIArtifact.subject_key == f"{surface}:{key}",
            AIArtifact.status == "complete",
        )
        .order_by(AIArtifact.created_at.desc())
        .limit(1)
    )
    artifact = result.scalar_one_or_none()
    if artifact and artifact.content_json:
        return TrendNarrativeResponse(**artifact.content_json)
    return None


@router.post(
    "/{surface}/{key}/narrative",
    response_model=TrendNarrativeResponse,
)
async def generate_trend_narrative(
    db: DbSession,
    surface: str,
    key: str,
) -> TrendNarrativeResponse:
    """Generate or retrieve a trend narrative (cache-first)."""
    trend = await _get_latest_trend_snapshot(db, surface, key)

    # ── Fetch top patent context for richer LLM narratives ──
    top_patents: list[dict[str, str]] = []
    if trend.top_patent_ids:
        from uuid import UUID

        from app.core.models import PatentPublication

        result = await db.execute(
            select(PatentPublication).where(
                PatentPublication.id.in_([UUID(pid) for pid in trend.top_patent_ids[:5]])
            )
        )
        for patent in result.scalars().all():
            abstract = (patent.abstract or "")[:200]
            top_patents.append(
                {
                    "title": patent.title or patent.doc_id or "",
                    "abstract_snippet": abstract.strip(),
                    "primary_assignee": (patent.assignees or [""])[0],
                    "cpc_codes": ", ".join(patent.cpc or []) or "N/A",
                }
            )

    from app.ai.trend_narrative import generate_trend_narrative as _gen

    data, _artifact_id = await _gen(db, trend, top_patents=top_patents or None)
    return TrendNarrativeResponse(**data)
