from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import Text, and_, func, select, text
from sqlalchemy.orm import load_only

from app.api.deps import DbSession
from app.core.enums import LegalStatus
from app.core.models import PatentPublication
from app.core.schemas import (
    ExpirySummary,
    PaginatedResponse,
    PatentDetailResponse,
    PatentListItem,
    StatsResponse,
    SummarySchema,
    TrendPoint,
    TrendResponse,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[PatentListItem])
async def list_patents(
    db: DbSession,
    office: str | None = None,
    kind_code: str | None = None,
    cpc_prefix: str | None = None,
    assignee: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    min_score: float | None = None,
    sort_by: str = Query(default="publication_date", regex="^(publication_date|interesting_score|created_at)$"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[PatentListItem]:
    """List patents with filtering and pagination."""
    conditions = []

    if office:
        conditions.append(PatentPublication.office == office)
    if kind_code:
        conditions.append(PatentPublication.kind_code == kind_code)
    if cpc_prefix:
        conditions.append(
            PatentPublication.cpc.cast(Text).like(f'%"{cpc_prefix}%')
        )
    if assignee:
        conditions.append(PatentPublication.assignees.contains([assignee]))
    if date_from:
        conditions.append(PatentPublication.publication_date >= date_from)
    if date_to:
        conditions.append(PatentPublication.publication_date <= date_to)
    if min_score is not None:
        conditions.append(PatentPublication.interesting_score >= min_score)

    base_query = select(PatentPublication)
    if conditions:
        base_query = base_query.where(and_(*conditions))

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    sort_column = getattr(PatentPublication, sort_by)
    if sort_order == "desc":
        sort_column = sort_column.desc().nulls_last()
    else:
        sort_column = sort_column.asc().nulls_last()

    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(sort_column).offset(offset).limit(page_size)
    )
    patents = result.scalars().all()

    items = [PatentListItem.from_patent(p) for p in patents]
    pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: DbSession) -> StatsResponse:
    """Get patent statistics for dashboard."""
    total_result = await db.execute(select(func.count(PatentPublication.id)))
    total_patents = total_result.scalar() or 0

    grants_result = await db.execute(
        select(func.count(PatentPublication.id)).where(
            PatentPublication.legal_status == "GRANTED"
        )
    )
    total_grants = grants_result.scalar() or 0

    apps_result = await db.execute(
        select(func.count(PatentPublication.id)).where(
            PatentPublication.legal_status == "PUBLISHED"
        )
    )
    total_applications = apps_result.scalar() or 0

    summarized_result = await db.execute(
        select(func.count(PatentPublication.id)).where(
            PatentPublication.summarized_at.isnot(None)
        )
    )
    summarized_count = summarized_result.scalar() or 0

    week_ago = date.today() - timedelta(days=7)
    week_result = await db.execute(
        select(func.count(PatentPublication.id)).where(
            PatentPublication.created_at >= week_ago
        )
    )
    patents_this_week = week_result.scalar() or 0

    cpc_rows = (
        await db.execute(
            text(
                """
                SELECT LEFT(cpc_val, 1) AS section, COUNT(*) AS count
                FROM patent_publications, jsonb_array_elements_text(cpc) AS cpc_val
                WHERE cpc_val IS NOT NULL AND cpc_val != ''
                GROUP BY section ORDER BY count DESC LIMIT 5
                """
            )
        )
    ).fetchall()
    top_cpc_sections = [{"section": r.section, "count": r.count} for r in cpc_rows]

    assignee_rows = (
        await db.execute(
            text(
                """
                SELECT assignee_val AS assignee, COUNT(*) AS count
                FROM patent_publications, jsonb_array_elements_text(assignees) AS assignee_val
                WHERE assignee_val IS NOT NULL AND assignee_val != ''
                GROUP BY assignee_val ORDER BY count DESC LIMIT 5
                """
            )
        )
    ).fetchall()
    top_assignees = [{"assignee": r.assignee, "count": r.count} for r in assignee_rows]

    return StatsResponse(
        total_patents=total_patents,
        total_grants=total_grants,
        total_applications=total_applications,
        summarized_count=summarized_count,
        patents_this_week=patents_this_week,
        top_cpc_sections=top_cpc_sections,
        top_assignees=top_assignees,
    )


@router.get("/expiry-summary", response_model=ExpirySummary)
async def get_expiry_summary(db: DbSession) -> ExpirySummary:
    """Get count of expiring patents within 30, 90, and 365 days."""
    today = date.today()

    async def count_expiring(days: int) -> int:
        cutoff = today + timedelta(days=days)
        r = await db.execute(
            select(func.count()).select_from(PatentPublication).where(
                and_(
                    PatentPublication.estimated_expiry_date >= today,
                    PatentPublication.estimated_expiry_date <= cutoff,
                    PatentPublication.legal_status == LegalStatus.GRANTED,
                )
            )
        )
        return r.scalar() or 0

    within_30 = await count_expiring(30)
    within_90 = await count_expiring(90)
    within_365 = await count_expiring(365)

    return ExpirySummary(
        within_30_days=within_30,
        within_90_days=within_90,
        within_365_days=within_365,
    )


@router.get("/trend", response_model=TrendResponse)
async def get_trend(db: DbSession) -> TrendResponse:
    """Get publication trend for the last 12 months."""
    twelve_months_ago = date.today().replace(day=1) - timedelta(days=365)
    result = await db.execute(
        select(
            func.date_trunc("month", PatentPublication.publication_date).label("month"),
            func.count().label("count"),
        )
        .where(PatentPublication.publication_date >= twelve_months_ago)
        .group_by(text("month"))
        .order_by(text("month"))
    )
    rows = result.fetchall()
    points = [
        TrendPoint(period=row.month.strftime("%Y-%m"), count=row.count)
        for row in rows
        if row.month
    ]
    return TrendResponse(points=points)


@router.get("/{patent_id}", response_model=PatentDetailResponse)
async def get_patent(db: DbSession, patent_id: UUID) -> PatentDetailResponse:
    """Get detailed patent information by ID."""
    result = await db.execute(
        select(PatentPublication).where(PatentPublication.id == patent_id)
    )
    patent = result.scalar_one_or_none()

    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")

    return PatentDetailResponse.from_patent(patent)


@router.get("/{patent_id}/summary", response_model=SummarySchema | None)
async def get_patent_summary(db: DbSession, patent_id: UUID) -> SummarySchema | None:
    """Get AI summary for a patent. Returns null if not yet summarized."""
    result = await db.execute(
        select(PatentPublication.summary, PatentPublication.summarized_at).where(
            PatentPublication.id == patent_id
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Patent not found")

    summary_data, summarized_at = row
    if not summary_data or not summarized_at:
        return None

    return SummarySchema(**summary_data)
