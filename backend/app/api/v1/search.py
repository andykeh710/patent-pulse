from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import and_, func, select

from app.api.deps import DbSession
from app.core.models import PatentPublication
from app.core.schemas import PaginatedResponse, PatentListItem

router = APIRouter()


@router.get("", response_model=PaginatedResponse[PatentListItem])
async def search_patents(
    db: DbSession,
    q: str = Query(..., min_length=3, description="Search query"),
    cpc: str | None = None,
    assignee: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[PatentListItem]:
    """
    Full-text search across patents.

    Searches title and abstract using PostgreSQL full-text search.
    """
    search_query = func.plainto_tsquery("english", q)

    conditions = [PatentPublication.search_vector.op("@@")(search_query)]

    if cpc:
        conditions.append(PatentPublication.cpc.contains([cpc]))
    if assignee:
        conditions.append(PatentPublication.assignees.contains([assignee]))
    if date_from:
        conditions.append(PatentPublication.publication_date >= date_from)
    if date_to:
        conditions.append(PatentPublication.publication_date <= date_to)

    base_query = select(PatentPublication).where(and_(*conditions))

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    rank = func.ts_rank(PatentPublication.search_vector, search_query)

    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(rank.desc()).offset(offset).limit(page_size)
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
