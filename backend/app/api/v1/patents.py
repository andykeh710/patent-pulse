from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import Text, and_, func, or_, select, text
from sqlalchemy.orm import load_only

from app.api.deps import DbSession
from app.core.enums import LegalStatus
from app.core.models import PatentPublication
from app.core.ai_models import AIRun, TrendSnapshot
from app.core.schemas import (
    ExpirySummary,
    FreshnessResponse,
    PaginatedResponse,
    PatentDetailResponse,
    PatentListItem,
    StatsResponse,
    SummarySchema,
    TrendPoint,
    TrendResponse,
)
from app.core.validators import validate_cpc_prefix
from app.ai.why_now import generate_why_now as generate_why_now_cached
from app.ai.opportunity_narrative import generate_opportunity_narrative as generate_opportunity_narrative_cached
from app.ai.trend_snapshot import generate_trend_snapshot as generate_trend_snapshot_cached
from app.ai.assignee_intelligence import generate_assignee_intelligence as generate_assignee_intelligence_cached

router = APIRouter()

_OFFICE_CODE_ALIASES = {
    "US": "USPTO",
    "EP": "EPO",
    "WO": "WIPO",
    "JP": "JPO",
    "CN": "CNIPA",
    "KR": "KIPO",
}
_SCORE_PERCENT_SCALE = 100.0


def _normalize_office_filter(office: str) -> str:
    value = office.strip().upper()
    return _OFFICE_CODE_ALIASES.get(value, value)


def _normalize_score_filter(score: float) -> float:
    if score >= 1:
        return score / _SCORE_PERCENT_SCALE
    return score


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
    max_score: float | None = None,
    sort_by: str = Query(default="publication_date", pattern="^(publication_date|interesting_score|opportunity_score|created_at)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[PatentListItem]:
    """List patents with filtering and pagination."""
    conditions = []

    if office:
        conditions.append(PatentPublication.office == _normalize_office_filter(office))
    if kind_code:
        conditions.append(PatentPublication.kind_code == kind_code)
    if cpc_prefix:
        cpc_prefix = validate_cpc_prefix(cpc_prefix)
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
        conditions.append(PatentPublication.interesting_score >= _normalize_score_filter(min_score))
    if max_score is not None:
        conditions.append(PatentPublication.interesting_score <= _normalize_score_filter(max_score))

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


@router.get("/freshness", response_model=FreshnessResponse)
async def get_freshness(db: DbSession) -> FreshnessResponse:
    """Return data freshness timestamps for UI indicators."""
    # Latest patent ingested
    latest_created = await db.execute(
        select(func.max(PatentPublication.created_at))
    )
    latest_patent_created_at = latest_created.scalar()

    # Latest publication date in the data
    latest_pub = await db.execute(
        select(func.max(PatentPublication.publication_date))
    )
    latest_pub_date = latest_pub.scalar()

    # Latest summarization
    latest_summ = await db.execute(
        select(func.max(PatentPublication.summarized_at))
    )
    latest_summarized_at = latest_summ.scalar()

    # Total counts
    total_result = await db.execute(select(func.count(PatentPublication.id)))
    total_patents = total_result.scalar() or 0

    summarized_result = await db.execute(
        select(func.count(PatentPublication.id)).where(
            PatentPublication.summarized_at.isnot(None)
        )
    )
    total_summarized = summarized_result.scalar() or 0

    # Latest trend snapshot
    latest_trend = await db.execute(
        select(func.max(TrendSnapshot.week_start))
    )
    latest_trend_val = latest_trend.scalar()

    trend_count = await db.execute(select(func.count(TrendSnapshot.id)))
    total_trend_snapshots = trend_count.scalar() or 0

    # Latest AI run
    latest_run = await db.execute(
        select(func.max(AIRun.created_at))
    )
    latest_ai_run_at = latest_run.scalar()

    return FreshnessResponse(
        latest_patent_created_at=latest_patent_created_at,
        latest_patent_publication_date=str(latest_pub_date) if latest_pub_date else None,
        latest_summarized_at=latest_summarized_at,
        latest_trend_snapshot_at=latest_trend_val,
        latest_ai_run_at=latest_ai_run_at,
        total_patents=total_patents,
        total_summarized=total_summarized,
        total_trend_snapshots=total_trend_snapshots,
    )


@router.get("/expiry-summary", response_model=ExpirySummary)
async def get_expiry_summary(db: DbSession) -> ExpirySummary:
    """Get count of expiring patents within 5, 10, and 20 years."""
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

    async def count_total_with_expiry() -> int:
        r = await db.execute(
            select(func.count()).select_from(PatentPublication).where(
                and_(
                    PatentPublication.estimated_expiry_date.isnot(None),
                    PatentPublication.legal_status == LegalStatus.GRANTED,
                )
            )
        )
        return r.scalar() or 0

    within_5y = await count_expiring(5 * 365)
    within_10y = await count_expiring(10 * 365)
    within_20y = await count_expiring(20 * 365)
    total = await count_total_with_expiry()

    return ExpirySummary(
        within_5_years=within_5y,
        within_10_years=within_10y,
        within_20_years=within_20y,
        total_with_expiry=total,
    )


@router.get("/trend", response_model=TrendResponse)
async def get_trend(db: DbSession) -> TrendResponse:
    """Get publication trend for the last 12 months."""
    today = date.today()
    # Go back exactly 12 calendar months
    year = today.year
    month = today.month - 12
    if month <= 0:
        month += 12
        year -= 1
    twelve_months_ago = date(year, month, 1)
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


@router.get("/priority-watch", response_model=PaginatedResponse[PatentListItem])
async def priority_watch(
    db: DbSession,
    bucket: str = Query(default="expiring_soon", pattern="^(expiring_soon|recent|all)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
) -> PaginatedResponse[PatentListItem]:
    """
    Patents that warrant immediate attention.

    Buckets:
    - `expiring_soon`: granted patents expiring within 5 years, ranked by urgency × score
    - `recent`: patents granted/published in last 90 days, ranked by interesting_score
    - `all`: union of the above, deduplicated, ranked by combined priority score
    """
    today = date.today()
    five_years = today + timedelta(days=5 * 365)
    ninety_days_ago = today - timedelta(days=90)

    if bucket == "expiring_soon":
        base_query = select(PatentPublication).where(
            and_(
                PatentPublication.estimated_expiry_date >= today,
                PatentPublication.estimated_expiry_date <= five_years,
                PatentPublication.legal_status == LegalStatus.GRANTED,
            )
        )
        # Order by expiry date ascending (soonest first), then by score descending
        order = (
            PatentPublication.estimated_expiry_date.asc().nullslast(),
            PatentPublication.interesting_score.desc().nullslast(),
        )
    elif bucket == "recent":
        base_query = select(PatentPublication).where(
            PatentPublication.publication_date >= ninety_days_ago
        )
        order = (
            PatentPublication.interesting_score.desc().nullslast(),
            PatentPublication.publication_date.desc().nullslast(),
        )
    else:  # all
        base_query = select(PatentPublication).where(
            or_(
                and_(
                    PatentPublication.estimated_expiry_date >= today,
                    PatentPublication.estimated_expiry_date <= five_years,
                    PatentPublication.legal_status == LegalStatus.GRANTED,
                ),
                PatentPublication.publication_date >= ninety_days_ago,
            )
        )
        order = (
            PatentPublication.interesting_score.desc().nullslast(),
            PatentPublication.estimated_expiry_date.asc().nullslast(),
        )

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.order_by(*order).offset(offset).limit(page_size)
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


_summarization_pending: set[str] = set()


@router.get("/{patent_id}/summary", response_model=SummarySchema | None)
async def get_patent_summary(db: DbSession, patent_id: UUID) -> SummarySchema | None:
    """Get AI summary for a patent. Triggers summarization if not yet done."""
    result = await db.execute(
        select(PatentPublication.summary, PatentPublication.summarized_at).where(
            PatentPublication.id == patent_id
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Patent not found")

    summary_data, summarized_at = row
    if summary_data and summarized_at:
        _summarization_pending.discard(str(patent_id))
        return SummarySchema(**summary_data)

    # Trigger summarization once — the frontend polls every 5s and will pick it up
    pid = str(patent_id)
    if pid not in _summarization_pending:
        _summarization_pending.add(pid)
        from app.tasks.summarize import summarize_patent

        summarize_patent.delay(pid)

    return None


@router.post("/{patent_id}/why-now", response_model=dict)
async def generate_why_now(
    db: DbSession,
    patent_id: UUID,
    force: bool = Query(default=False),
) -> dict:
    """Generate or retrieve the Why Now narrative for a patent.

    Cache-first: returns the existing AIArtifact if one matches the current
    input fingerprint.  Pass ``force=true`` to bypass the cache and regenerate.
    """
    result = await db.execute(
        select(PatentPublication).where(PatentPublication.id == patent_id)
    )
    patent = result.scalar_one_or_none()
    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")

    if not patent.title and not patent.abstract:
        raise HTTPException(
            status_code=400, detail="Patent has no title or abstract to analyze"
        )

    data, artifact_id = await generate_why_now_cached(
        db, patent, run_id=None
    )

    # Denormalize onto PatentPublication for fast reads
    patent.why_now_text = data.get("headline", "")
    patent.latest_why_now_artifact_id = artifact_id
    await db.commit()

    return {
        "status": "success",
        "artifact_id": str(artifact_id),
        "headline": data.get("headline", ""),
        "summary": data.get("summary", ""),
        "signals": data.get("signals", []),
        "confidence": data.get("confidence", "low"),
        "limitations": data.get("limitations", []),
    }


@router.post("/{patent_id}/opportunity-narrative", response_model=dict)
async def generate_opportunity_narrative(
    db: DbSession,
    patent_id: UUID,
    force: bool = Query(default=False),
) -> dict:
    """Generate or retrieve the Opportunity Narrative for a patent.

    Cache-first: returns the existing AIArtifact if one matches the current
    input fingerprint.  Pass ``force=true`` to bypass the cache and regenerate.
    """
    result = await db.execute(
        select(PatentPublication).where(PatentPublication.id == patent_id)
    )
    patent = result.scalar_one_or_none()
    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")

    if not patent.title and not patent.abstract:
        raise HTTPException(
            status_code=400, detail="Patent has no title or abstract to analyze"
        )

    data, artifact_id = await generate_opportunity_narrative_cached(
        db, patent, run_id=None
    )

    return {
        "status": "success",
        "artifact_id": str(artifact_id),
        "opportunity_type": data.get("opportunity_type", ""),
        "plain_english_opportunity": data.get("plain_english_opportunity", ""),
        "possible_products": data.get("possible_products", []),
        "target_customers": data.get("target_customers", []),
        "implementation_difficulty": data.get("implementation_difficulty", "unknown"),
        "commercial_timing": data.get("commercial_timing", "uncertain"),
        "risks": data.get("risks", []),
    }


@router.post("/{patent_id}/trend-snapshot", response_model=dict)
async def generate_trend_snapshot(
    db: DbSession,
    patent_id: UUID,
    force: bool = Query(default=False),
) -> dict:
    """Generate or retrieve the Trend Snapshot for a patent.

    Cache-first via :func:`app.ai.llm_client.record_rules_artifact`.
    Pass ``force=true`` to bypass the cache.
    """
    result = await db.execute(
        select(PatentPublication).where(PatentPublication.id == patent_id)
    )
    patent = result.scalar_one_or_none()
    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")

    data, artifact_id = await generate_trend_snapshot_cached(
        db, patent, run_id=None
    )
    await db.commit()

    return {
        "status": "success",
        "artifact_id": str(artifact_id),
        "trend_score": data.get("trend_score", 0.0),
        "components": data.get("components", {}),
    }


@router.post("/{patent_id}/assignee-intelligence", response_model=dict)
async def generate_assignee_intelligence(
    db: DbSession,
    patent_id: UUID,
    force: bool = Query(default=False),
) -> dict:
    """Generate or retrieve the Assignee Intelligence for a patent.

    Cache-first via :func:`app.ai.llm_client.record_rules_artifact`.
    Pass ``force=true`` to bypass the cache.
    """
    result = await db.execute(
        select(PatentPublication).where(PatentPublication.id == patent_id)
    )
    patent = result.scalar_one_or_none()
    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")

    data, artifact_id = await generate_assignee_intelligence_cached(
        db, patent, run_id=None
    )
    await db.commit()

    return {
        "status": "success",
        "artifact_id": str(artifact_id),
        "assignee_intelligence_score": data.get("assignee_intelligence_score", 0.0),
        "components": data.get("components", {}),
    }
