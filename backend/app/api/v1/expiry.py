"""Expiry API — Sprint 2B upgrade with ExpiryAssessment integration."""
from datetime import date, timedelta

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import Text, and_, func, or_, select, text

from app.api.deps import DbSession
from app.core.ai_models import ExpiryAssessment, PatentUsageSignals
from app.core.enums import LegalStatus
from app.core.models import PatentPublication
from app.core.schemas import ExpiryItem, PaginatedResponse
from app.core.validators import validate_industry

router = APIRouter()

# Allowed filter values (kept in sync with assessment engine).
ALLOWED_EXPIRY_STATUSES = {
    "active_estimated", "expiring_soon", "expired_estimated",
    "lapsed_possible", "lapsed_confirmed", "expired_confirmed", "unknown",
}
ALLOWED_CONFIDENCE = {"low", "medium", "high", "confirmed"}


# ── response schemas ─────────────────────────────────────────────────


class ExpirySummaryResponse(BaseModel):
    total_with_expiry: int
    by_status: dict[str, int]
    by_confidence: dict[str, int]
    with_family_risk: int
    without_family_risk: int
    high_opportunity_count: int
    by_maintenance: dict[str, int]


class ExpiryOpportunityItem(BaseModel):
    id: str
    doc_id: str
    title: str | None
    assignees: list[str]
    estimated_expiry_date: date | None
    expiry_status: str
    expiry_status_confidence: str
    active_family_risk: bool
    expiry_opportunity_score: float | None
    opportunity_score: float | None
    days_until_expiry: int | None
    # Sprint 5 — surfaced via LEFT JOIN on patent_usage_signals.
    usage_signal_score: float | None = None
    usage_signal_evidence_count: int | None = None
    usage_has_self_citation_risk: bool | None = None


class ExpiryOpportunityResponse(BaseModel):
    items: list[ExpiryOpportunityItem]
    total: int


# ── main list endpoint (upgraded) ─────────────────────────────────────


@router.get("", response_model=PaginatedResponse[ExpiryItem])
async def list_expiring_patents(
    db: DbSession,
    days_ahead: int = Query(default=365, ge=0, le=7300),
    office: str | None = None,
    industry: str | None = None,
    time_horizon: str | None = None,
    # ── new Sprint 2B filters ──
    expiry_status: str | None = Query(default=None, description="Filter by expiry_status"),
    confidence: str | None = Query(default=None, description="Filter by expiry_status_confidence"),
    maintenance_status: str | None = None,
    active_family_risk: bool | None = None,
    min_expiry_opportunity_score: float | None = Query(default=None, ge=0, le=100),
    # ── Sprint 2C: backward-looking window ──
    expiry_window_start: date | None = Query(
        default=None,
        description="Lower bound for estimated_expiry_date. Defaults to today (forward-looking). Set to a past date to query expired patents.",
    ),
    # ── Sprint 5: usage signals filter ──
    has_usage_signals: bool | None = Query(
        default=None,
        description="Filter by whether usage signals have been assessed (true) or not (false).",
    ),
    # ── sorts ──
    sort_by: str = Query(
        default="expiry_urgency",
        pattern="^(expiry_urgency|expiry_date|opportunity_score|expiry_opportunity_score|confidence|recently_assessed)$",
    ),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ExpiryItem]:
    """List patents approaching expiration, enriched with ExpiryAssessment data."""
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)

    # Build a query that LEFT JOINs ExpiryAssessment.
    # Use a subquery approach: select PatentPublication + optional assessment fields.
    base_query = (
        select(
            PatentPublication,
            ExpiryAssessment.expiry_status,
            ExpiryAssessment.expiry_status_confidence,
            ExpiryAssessment.active_family_risk,
            ExpiryAssessment.maintenance_status,
            ExpiryAssessment.expiry_opportunity_score,
            PatentUsageSignals.usage_signal_score,
            PatentUsageSignals.evidence_count.label("usage_signal_evidence_count"),
            PatentUsageSignals.has_self_citation_risk.label("usage_has_self_citation_risk"),
        )
        .outerjoin(
            ExpiryAssessment,
            ExpiryAssessment.patent_publication_id == PatentPublication.id,
        )
        .outerjoin(
            PatentUsageSignals,
            PatentUsageSignals.patent_publication_id == PatentPublication.id,
        )
    )

    conditions = [
        PatentPublication.estimated_expiry_date >= (expiry_window_start or today),
        PatentPublication.estimated_expiry_date <= cutoff,
        PatentPublication.legal_status == LegalStatus.GRANTED,
    ]

    if office:
        conditions.append(PatentPublication.office == office)

    if industry:
        industry = validate_industry(industry)
        conditions.append(
            PatentPublication.tags.op("->")("industries").cast(Text).like(f'%"%{industry}"%')
        )

    if time_horizon:
        conditions.append(
            PatentPublication.tags.op("->>")(("time_horizon")) == time_horizon
        )

    # Sprint 2B: assessment-level filters.
    if expiry_status and expiry_status in ALLOWED_EXPIRY_STATUSES:
        conditions.append(ExpiryAssessment.expiry_status == expiry_status)
    if confidence and confidence in ALLOWED_CONFIDENCE:
        conditions.append(ExpiryAssessment.expiry_status_confidence == confidence)
    if maintenance_status:
        conditions.append(ExpiryAssessment.maintenance_status == maintenance_status)
    if active_family_risk is not None:
        conditions.append(ExpiryAssessment.active_family_risk == active_family_risk)
    if has_usage_signals is not None:
        if has_usage_signals:
            conditions.append(PatentUsageSignals.patent_publication_id.isnot(None))
        else:
            conditions.append(PatentUsageSignals.patent_publication_id.is_(None))
    if min_expiry_opportunity_score is not None:
        conditions.append(
            ExpiryAssessment.expiry_opportunity_score >= min_expiry_opportunity_score
        )

    base_query = base_query.where(and_(*conditions))

    # Count.
    count_subq = base_query.subquery()
    count_result = await db.execute(
        select(func.count()).select_from(count_subq)
    )
    total = count_result.scalar() or 0

    # Sort.
    if sort_by == "expiry_urgency":
        order_clauses = [
            PatentPublication.estimated_expiry_date.asc(),
            PatentPublication.opportunity_score.desc(),
        ]
    elif sort_by == "expiry_date":
        order_clauses = [
            PatentPublication.estimated_expiry_date.asc() if sort_order == "asc"
            else PatentPublication.estimated_expiry_date.desc()
        ]
    elif sort_by == "opportunity_score":
        order_clauses = [
            PatentPublication.opportunity_score.desc() if sort_order == "desc"
            else PatentPublication.opportunity_score.asc()
        ]
    elif sort_by == "expiry_opportunity_score":
        order_clauses = [
            ExpiryAssessment.expiry_opportunity_score.desc() if sort_order == "desc"
            else ExpiryAssessment.expiry_opportunity_score.asc()
        ]
    elif sort_by == "confidence":
        # Map confidence to integer for sorting: confirmed=4, high=3, medium=2, low=1.
        conf_order = {"confirmed": 4, "high": 3, "medium": 2, "low": 1}
        order_clauses = [
            text(
                f"CASE expiry_assessments.expiry_status_confidence "
                + " ".join(
                    f"WHEN '{k}' THEN {v}" for k, v in conf_order.items()
                )
                + " ELSE 0 END " + ("DESC" if sort_order == "desc" else "ASC")
            )
        ]
    elif sort_by == "recently_assessed":
        order_clauses = [
            ExpiryAssessment.computed_at.desc() if sort_order == "desc"
            else ExpiryAssessment.computed_at.asc()
        ]
    else:
        order_clauses = [
            PatentPublication.estimated_expiry_date.asc(),
            PatentPublication.opportunity_score.desc(),
        ]

    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(*order_clauses).offset(offset).limit(page_size)
    )
    rows = result.all()

    items = []
    for row in rows:
        patent = row[0]
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
                legal_status_confidence=getattr(patent, "legal_status_confidence", None)
                or "estimated",
                opportunity_score=getattr(patent, "opportunity_score", None),
                tags=getattr(patent, "tags", None),
                # Sprint 2B: assessment fields from row indices 1-5.
                expiry_status=row[1] if len(row) > 1 else None,
                expiry_status_confidence=row[2] if len(row) > 2 else None,
                active_family_risk=row[3] if len(row) > 3 else None,
                maintenance_status=row[4] if len(row) > 4 else None,
                expiry_opportunity_score=row[5] if len(row) > 5 else None,
                # Sprint 5: usage signals from row indices 6-7.
                usage_signal_score=row[6] if len(row) > 6 else None,
                usage_signal_evidence_count=row[7] if len(row) > 7 else None,
                usage_has_self_citation_risk=row[8] if len(row) > 8 else None,
                # Sprint 2C: CSV export metadata.
                publication_number=patent.publication_number,
                office=patent.office,
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


# ── summary endpoint ──────────────────────────────────────────────────


@router.get("/summary", response_model=ExpirySummaryResponse)
async def expiry_summary(db: DbSession) -> ExpirySummaryResponse:
    """Return grouped counts for the Expiry Radar dashboard."""
    # Total patents with estimated expiry dates.
    total_result = await db.execute(
        select(func.count(PatentPublication.id)).where(
            PatentPublication.estimated_expiry_date.isnot(None)
        )
    )
    total_with_expiry = total_result.scalar() or 0

    # Counts by status.
    status_result = await db.execute(
        select(
            ExpiryAssessment.expiry_status,
            func.count(ExpiryAssessment.id),
        ).group_by(ExpiryAssessment.expiry_status)
    )
    by_status: dict[str, int] = {}
    for status, cnt in status_result.all():
        by_status[status] = cnt

    # Counts by confidence.
    conf_result = await db.execute(
        select(
            ExpiryAssessment.expiry_status_confidence,
            func.count(ExpiryAssessment.id),
        ).group_by(ExpiryAssessment.expiry_status_confidence)
    )
    by_confidence: dict[str, int] = {}
    for conf, cnt in conf_result.all():
        by_confidence[conf] = cnt

    # Family risk counts.
    risk_result = await db.execute(
        select(
            ExpiryAssessment.active_family_risk,
            func.count(ExpiryAssessment.id),
        ).group_by(ExpiryAssessment.active_family_risk)
    )
    with_family_risk = 0
    without_family_risk = 0
    for risk, cnt in risk_result.all():
        if risk:
            with_family_risk = cnt
        else:
            without_family_risk = cnt

    # High-opportunity count (score >= 50).
    high_opp_result = await db.execute(
        select(func.count(ExpiryAssessment.id)).where(
            ExpiryAssessment.expiry_opportunity_score >= 50
        )
    )
    high_opportunity_count = high_opp_result.scalar() or 0

    # By maintenance status.
    maint_result = await db.execute(
        select(
            ExpiryAssessment.maintenance_status,
            func.count(ExpiryAssessment.id),
        ).group_by(ExpiryAssessment.maintenance_status)
    )
    by_maintenance: dict[str, int] = {}
    for maint, cnt in maint_result.all():
        by_maintenance[maint] = cnt

    return ExpirySummaryResponse(
        total_with_expiry=total_with_expiry,
        by_status=by_status,
        by_confidence=by_confidence,
        with_family_risk=with_family_risk,
        without_family_risk=without_family_risk,
        high_opportunity_count=high_opportunity_count,
        by_maintenance=by_maintenance,
    )


# ── opportunities endpoint ────────────────────────────────────────────


@router.get("/opportunities", response_model=ExpiryOpportunityResponse)
async def expiry_opportunities(
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    min_score: float = Query(default=30, ge=0, le=100),
) -> ExpiryOpportunityResponse:
    """Return high-value expiry opportunity candidates."""
    today = date.today()

    result = await db.execute(
        select(
            PatentPublication,
            ExpiryAssessment,
            PatentUsageSignals.usage_signal_score,
            PatentUsageSignals.evidence_count.label("usage_signal_evidence_count"),
            PatentUsageSignals.has_self_citation_risk.label("usage_has_self_citation_risk"),
        )
        .join(
            ExpiryAssessment,
            ExpiryAssessment.patent_publication_id == PatentPublication.id,
        )
        .outerjoin(
            PatentUsageSignals,
            PatentUsageSignals.patent_publication_id == PatentPublication.id,
        )
        .where(
            ExpiryAssessment.expiry_opportunity_score >= min_score,
        )
        .order_by(ExpiryAssessment.expiry_opportunity_score.desc())
        .limit(limit)
    )
    rows = result.all()

    items = []
    for row in rows:
        patent, assessment, signal_score, signal_ev_count, signal_self_cite = row
        days_until = None
        if patent.estimated_expiry_date:
            days_until = (patent.estimated_expiry_date - today).days

        items.append(
            ExpiryOpportunityItem(
                id=str(patent.id),
                doc_id=patent.doc_id,
                title=patent.title,
                assignees=patent.assignees or [],
                estimated_expiry_date=patent.estimated_expiry_date,
                expiry_status=assessment.expiry_status,
                expiry_status_confidence=assessment.expiry_status_confidence,
                active_family_risk=assessment.active_family_risk,
                expiry_opportunity_score=assessment.expiry_opportunity_score,
                opportunity_score=patent.opportunity_score,
                days_until_expiry=days_until,
                usage_signal_score=signal_score,
                usage_signal_evidence_count=signal_ev_count,
                usage_has_self_citation_risk=signal_self_cite,
            )
        )

    return ExpiryOpportunityResponse(items=items, total=len(items))
