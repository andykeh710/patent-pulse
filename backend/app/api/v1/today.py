"""
Today page highlights — query-driven editorial cards.

Four cards, each from real data, no LLM. Cards hide individually
when their query returns empty.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import desc, func, select, text

from app.api.deps import DbSession, current_user, get_db
from app.core.ai_models import TrendSnapshot
from app.core.models import PatentPublication
from app.services.briefing import assemble_briefing

router = APIRouter()

# ── For You (personalized recommendations) ──────────────


@router.get("/for-you")
async def get_for_you(
    db=Depends(get_db),
    user_id: str = Depends(current_user),
) -> list[dict]:
    """Personalized patent recommendations based on viewing history."""
    from app.services.recommendations import recommend_for_user

    recs = await recommend_for_user(user_id, limit=5, session=db)
    items: list[dict] = []
    now = datetime.now(timezone.utc)

    for r in recs:
        items.append(dict(
            type="foryou", label="For You",
            title=r["title"],
            subtext=f"{r['assignee']} · {r['patent_id'][:8]}",
            reason="Recommended based on your patent viewing patterns",
            source="Invention Index 8",
            freshness={"updated_at": now.isoformat(), "relative": "just now"},
            confidence={"level": "medium", "caveat": "AI recommendation"},
            href=f"/patents/{r['patent_id']}",
        ))

    if not items:
        items.append(dict(
            type="foryou", label="For You · early personalization",
            title="Recommendations appear as you explore patents and follow topics",
            reason="Based on your activity and follows",
            source="Invention Index 8",
            freshness={"updated_at": now.isoformat(), "relative": "just now"},
            href="/themes",
        ))

    return items


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class FilingTrendCard(BaseModel):
    """Card 1 — trend with highest z_score updated in last 7 days."""

    trend_surface: str
    trend_key: str
    trend_label: str  # human-readable (CPC label or key)
    count_4w: int
    z_score: float
    top_assignees: list[str]  # distinct assignees from top_patent_ids
    top_patent_ids: list[str]


class ExpiringOpportunityCard(BaseModel):
    """Card 2 — count of high-opportunity patents expiring within 90 days."""

    count: int
    caveat: str = "Verify with official registers before relying on expiry status."


class NotablePatentCard(BaseModel):
    """Card 3 — highest opportunity_score patent from last 14 days with a summary."""

    id: UUID
    publication_number: str
    doc_id: str
    title: str | None
    assignee: str
    opportunity_score: float
    summary_first_sentence: str
    has_abstract: bool
    has_claims: bool
    limited_source: bool  # True if missing abstract OR claims


class CompanyMoveCard(BaseModel):
    """Card 4 — assignee with largest filing delta (this week vs 4wk avg)."""

    assignee: str
    count_this_week: int
    count_4wk_avg: float
    delta: int


class TodayHighlightsResponse(BaseModel):
    filing_trend: FilingTrendCard | None = None
    expiring_opportunity: ExpiringOpportunityCard | None = None
    notable_patent: NotablePatentCard | None = None
    company_move: CompanyMoveCard | None = None


# ---------------------------------------------------------------------------
# CPC label lookup (shared with trends)
# ---------------------------------------------------------------------------

CPC_LABELS: dict[str, str] = {
    "A61B": "Medical Diagnostics",
    "A61F": "Medical Implants",
    "A61K": "Pharma / Drug Delivery",
    "A61M": "Medical Devices",
    "B01D": "Separation / Filtration",
    "B29K": "Plastics / Polymers",
    "B32B": "Layered Materials",
    "B60W": "Vehicle Control",
    "C07K": "Peptides / Proteins",
    "C12N": "Biotech / Genetics",
    "G01N": "Testing / Analysis",
    "G06F": "Computing / Processing",
    "G06T": "Image Processing",
    "G06V": "Computer Vision",
    "G09G": "Display Control",
    "H01M": "Batteries / Fuel Cells",
    "H04L": "Network Protocols",
    "H04W": "Wireless Communication",
    "H05K": "Printed Circuits",
    "H10W": "Semiconductor Devices",
    "Y02E": "Clean Energy",
    "Y10T": "Technical Subjects",
}


def _cpc_label(key: str) -> str:
    return CPC_LABELS.get(key, key)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


async def _query_filing_trend(db: DbSession) -> FilingTrendCard | None:
    """Trend with highest z_score whose week_start is in the last 7 days."""
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    result = await db.execute(
        select(TrendSnapshot)
        .where(
            TrendSnapshot.week_start >= seven_days_ago,
            TrendSnapshot.z_score > 0,
        )
        .order_by(desc(TrendSnapshot.z_score))
        .limit(1)
    )
    trend = result.scalar_one_or_none()
    if not trend:
        return None

    # Derive top assignees from top_patent_ids
    top_assignees: list[str] = []
    if trend.top_patent_ids:
        assignee_result = await db.execute(
            select(PatentPublication.assignees)
            .where(PatentPublication.id.in_(
                [UUID(pid) for pid in trend.top_patent_ids[:5]]
            ))
        )
        seen: set[str] = set()
        for (assignees,) in assignee_result:
            for a in (assignees or []):
                if a not in seen:
                    seen.add(a)
                    top_assignees.append(a)
                if len(top_assignees) >= 3:
                    break
            if len(top_assignees) >= 3:
                break

    label = _cpc_label(trend.key) if trend.surface == "cpc" else trend.key
    return FilingTrendCard(
        trend_surface=trend.surface,
        trend_key=trend.key,
        trend_label=f"{trend.key} — {label}" if trend.surface == "cpc" else label,
        count_4w=trend.count_4w,
        z_score=round(trend.z_score, 1),
        top_assignees=top_assignees,
        top_patent_ids=trend.top_patent_ids[:3] if trend.top_patent_ids else [],
    )


async def _query_expiring_opportunity(db: DbSession) -> ExpiringOpportunityCard | None:
    """Count patents with expiry_opportunity_score > 70 expiring in next 90 days."""
    now = datetime.utcnow().date()
    ninety_days = now + timedelta(days=90)

    # expiry_opportunity_score is stored in opportunity_breakdown JSON
    # or as a separate column. Check the opportunity_breakdown column.
    result = await db.execute(
        select(func.count(PatentPublication.id))
        .where(
            PatentPublication.estimated_expiry_date.isnot(None),
            PatentPublication.estimated_expiry_date >= now,
            PatentPublication.estimated_expiry_date <= ninety_days,
            PatentPublication.opportunity_score.isnot(None),
            PatentPublication.opportunity_score > 70,
        )
    )
    count = result.scalar() or 0
    if count == 0:
        return None

    return ExpiringOpportunityCard(count=count)


async def _query_notable_patent(db: DbSession) -> NotablePatentCard | None:
    """Highest opportunity_score patent from last 60 days that has a summary."""
    sixty_days_ago = datetime.utcnow() - timedelta(days=60)

    result = await db.execute(
        select(PatentPublication)
        .where(
            PatentPublication.created_at >= sixty_days_ago,
            PatentPublication.opportunity_score.isnot(None),
            PatentPublication.opportunity_score > 30,
            PatentPublication.summary.isnot(None),
            # Exclude nonsensical / placeholder summaries
            ~PatentPublication.summary["what_it_is"].as_string().like("Unable to determine%"),
            ~PatentPublication.summary["what_it_is"].as_string().like(""),
            PatentPublication.summary["what_it_is"].as_string().isnot(None),
        )
        .order_by(desc(PatentPublication.opportunity_score))
        .limit(1)
    )
    patent = result.scalar_one_or_none()
    if not patent:
        return None

    # Extract first sentence from summary
    summary_text = ""
    if patent.summary and isinstance(patent.summary, dict):
        summary_text = (
            patent.summary.get("what_it_is")
            or patent.summary.get("summary")
            or ""
        )
    first_sentence = summary_text.split(".")[0].strip() + "." if summary_text else ""

    has_abstract = bool(patent.abstract)
    has_claims = bool(patent.claims_text)

    return NotablePatentCard(
        id=patent.id,
        publication_number=patent.publication_number,
        doc_id=patent.doc_id,
        title=patent.title,
        assignee=(patent.assignees or ["Unknown"])[0],
        opportunity_score=round(patent.opportunity_score or 0, 1),
        summary_first_sentence=first_sentence,
        has_abstract=has_abstract,
        has_claims=has_claims,
        limited_source=not has_abstract or not has_claims,
    )


async def _query_company_move(db: DbSession) -> CompanyMoveCard | None:
    """Assignee with largest delta (this week vs 4wk avg) where delta >= 5.

    Uses publication_date (when the patent was published) not created_at
    (when it was ingested) to avoid inflating counts from bulk backfills.
    """
    today = datetime.utcnow().date()
    this_week_start = today - timedelta(days=7)
    four_weeks_ago = today - timedelta(days=28)

    # Count filings per assignee this week
    this_week = await db.execute(
        select(
            func.jsonb_array_elements_text(PatentPublication.assignees).label("assignee"),
            func.count(PatentPublication.id).label("cnt"),
        )
        .where(PatentPublication.publication_date >= this_week_start)
        .group_by(text("assignee"))
    )
    this_week_counts: dict[str, int] = {
        row.assignee: row.cnt for row in this_week
    }

    # Count filings per assignee in prior 3 weeks (4wk window minus this week)
    prior_3wk = await db.execute(
        select(
            func.jsonb_array_elements_text(PatentPublication.assignees).label("assignee"),
            func.count(PatentPublication.id).label("cnt"),
        )
        .where(
            PatentPublication.publication_date >= four_weeks_ago,
            PatentPublication.publication_date < this_week_start,
        )
        .group_by(text("assignee"))
    )
    prior_counts: dict[str, int] = {
        row.assignee: row.cnt for row in prior_3wk
    }

    # Find max delta
    best_assignee: str | None = None
    best_delta: int = 0
    best_count: int = 0
    best_avg: float = 0.0

    for assignee, count in this_week_counts.items():
        prior = prior_counts.get(assignee, 0)
        avg = prior / 3.0 if prior > 0 else 0.0
        delta = count - int(avg)
        if delta >= 5 and delta > best_delta:
            best_assignee = assignee
            best_delta = delta
            best_count = count
            best_avg = avg

    if not best_assignee:
        return None

    return CompanyMoveCard(
        assignee=best_assignee,
        count_this_week=best_count,
        count_4wk_avg=round(best_avg, 1),
        delta=best_delta,
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/highlights", response_model=TodayHighlightsResponse)
async def get_highlights(db: DbSession) -> TodayHighlightsResponse:
    """Return editorial highlight cards for the Today page.

    Queries run sequentially against a single async session
    (SQLAlchemy async sessions don't support concurrent operations).
    Each card is null when its query returns no data — the frontend
    hides empty cards.
    """
    trend = await _query_filing_trend(db)
    expiry = await _query_expiring_opportunity(db)
    notable = await _query_notable_patent(db)
    company = await _query_company_move(db)

    return TodayHighlightsResponse(
        filing_trend=trend,
        expiring_opportunity=expiry,
        notable_patent=notable,
        company_move=company,
    )


# ── Briefing feed ──────────────────────────────────────────


@router.get("/briefing")
async def get_briefing(db: DbSession) -> list[dict]:
    """Return a weighted briefing feed for the Today page.

    Each item includes required fields: type, label, title, reason,
    source, freshness, confidence, href.
    """
    return await assemble_briefing(db)
