from datetime import date, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import and_, func, select

from app.api.deps import DbSession
from app.core.enums import LegalStatus
from app.core.models import PatentPublication
from app.core.schemas import ExpiryItem, PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ExpiryItem])
async def list_expiring_patents(
    db: DbSession,
    days_ahead: int = Query(default=365, ge=1, le=3650),
    office: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ExpiryItem]:
    """
    List patents approaching expiration.

    Returns granted patents with estimated expiry dates within the specified window.
    """
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)

    conditions = [
        PatentPublication.estimated_expiry_date >= today,
        PatentPublication.estimated_expiry_date <= cutoff,
        PatentPublication.legal_status == LegalStatus.GRANTED,
    ]

    if office:
        conditions.append(PatentPublication.office == office)

    base_query = select(PatentPublication).where(and_(*conditions))

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(PatentPublication.estimated_expiry_date.asc())
        .offset(offset)
        .limit(page_size)
    )
    patents = result.scalars().all()

    items = []
    for patent in patents:
        days_until = None
        if patent.estimated_expiry_date:
            days_until = (patent.estimated_expiry_date - today).days

        items.append(
            ExpiryItem(
                id=patent.id,
                doc_id=patent.doc_id,
                title=patent.title,
                assignees=patent.assignees or [],
                estimated_expiry_date=patent.estimated_expiry_date,
                days_until_expiry=days_until,
                legal_status=patent.legal_status,
            )
        )

    pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
