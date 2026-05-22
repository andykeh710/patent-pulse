from datetime import date, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import Text, and_, func, or_, select, text

from app.api.deps import DbSession
from app.core.enums import LegalStatus
from app.core.models import PatentPublication
from app.core.schemas import ExpiryItem, PaginatedResponse
from app.core.validators import validate_industry

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ExpiryItem])
async def list_expiring_patents(
    db: DbSession,
    days_ahead: int = Query(default=365, ge=1, le=7300),
    office: str | None = None,
    industry: str | None = None,
    time_horizon: str | None = None,
    sort_by: str = Query(default="expiry_urgency", pattern="^(expiry_urgency|expiry_date|opportunity_score)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ExpiryItem]:
    """
    List patents approaching expiration.

    Returns granted patents with estimated expiry dates within the specified window.
    Default sort prioritizes patents expiring soon with high opportunity scores.
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

    if industry:
        industry = validate_industry(industry)
        conditions.append(
            PatentPublication.tags.op("->")("industries").cast(Text).like(f'%"{industry}"%')
        )

    if time_horizon:
        conditions.append(
            PatentPublication.tags.op("->>")("time_horizon") == time_horizon
        )

    base_query = select(PatentPublication).where(and_(*conditions))

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    # Default sort: expiry urgency (days_until asc, nulls last) then opportunity_score desc
    if sort_by == "expiry_urgency":
        order = [
            PatentPublication.estimated_expiry_date.asc(),
            PatentPublication.opportunity_score.desc(),
        ]
    elif sort_by == "expiry_date":
        order = [
            PatentPublication.estimated_expiry_date.asc() if sort_order == "asc"
            else PatentPublication.estimated_expiry_date.desc()
        ]
    else:  # opportunity_score
        order = [
            PatentPublication.opportunity_score.desc() if sort_order == "desc"
            else PatentPublication.opportunity_score.asc()
        ]

    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(*order)
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
                legal_status_confidence=getattr(
                    patent, "legal_status_confidence", None
                ) or "estimated",
                opportunity_score=getattr(patent, "opportunity_score", None),
                tags=getattr(patent, "tags", None),
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
