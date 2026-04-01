from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import Text, and_, func, select
from sqlalchemy.orm import load_only

from app.api.deps import DbSession
from app.core.models import PatentPublication
from app.core.schemas import (
    PaginatedResponse,
    PatentDetailResponse,
    PatentListItem,
    StatsResponse,
    SummarySchema,
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

    return StatsResponse(
        total_patents=total_patents,
        total_grants=total_grants,
        total_applications=total_applications,
        summarized_count=summarized_count,
        patents_this_week=patents_this_week,
        top_cpc_sections=[],
        top_assignees=[],
    )


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
