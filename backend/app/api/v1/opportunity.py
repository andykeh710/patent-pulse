"""
Opportunity API.

Phase 1 surface for the ``/opportunity`` page. Returns a paginated,
filterable, sortable list of patents ranked by ``opportunity_score``.

Tabs (the ``tab`` query param) translate into preset filter combinations
documented inline; arbitrary filters can also be combined directly via
the explicit query params.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, cast, func, or_, select, text
from sqlalchemy.dialects.postgresql import JSONB, array

from app.api.deps import DbSession
from app.core.models import PatentPublication
from app.core.schemas import PaginatedResponse, PatentListItem

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class OpportunityItem(BaseModel):
    """One row in the /opportunity list."""

    id: UUID
    doc_id: str
    title: str | None = None
    assignees: list[str] = []
    cpc: list[str] = []
    publication_date: date | None = None
    grant_date: date | None = None
    estimated_expiry_date: date | None = None
    days_until_expiry: int | None = None
    legal_status: str | None = None
    legal_status_confidence: str = "estimated"

    interesting_score: float | None = None
    opportunity_score: float | None = None
    opportunity_score_version: int | None = None
    opportunity_breakdown: dict | None = None

    tags: dict | None = None
    summary_what_it_is: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_patent(cls, p: PatentPublication) -> "OpportunityItem":
        days = None
        if p.estimated_expiry_date:
            days = (p.estimated_expiry_date - date.today()).days
        summary_what = None
        if p.summary and isinstance(p.summary, dict):
            summary_what = p.summary.get("what_it_is")
        return cls(
            id=p.id,
            doc_id=p.doc_id,
            title=p.title,
            assignees=p.assignees or [],
            cpc=p.cpc or [],
            publication_date=p.publication_date,
            grant_date=p.grant_date,
            estimated_expiry_date=p.estimated_expiry_date,
            days_until_expiry=days,
            legal_status=p.legal_status,
            legal_status_confidence=p.legal_status_confidence or "estimated",
            interesting_score=p.interesting_score,
            opportunity_score=p.opportunity_score,
            opportunity_score_version=p.opportunity_score_version,
            opportunity_breakdown=p.opportunity_breakdown,
            tags=p.tags,
            summary_what_it_is=summary_what,
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


_Tab = Literal[
    "top",
    "expired",
    "revival",
    "cross_industry",
    "startup",
    "enterprise",
    "sustainability",
    "legal_review",
]

_Sort = Literal[
    "opportunity_score",
    "expiring_soon",
    "newly_published",
    "interesting_score",
    "lowest_legal_risk",
    "strongest_cross_industry",
]


def _tag_contains(_field, key: str, values: list[str]):
    """Build a ``patent.tags->'<key>' ?| ARRAY[...]`` predicate.

    Uses SQLAlchemy's native JSONB ``has_any`` operator on the indexed
    sub-element (cast back to JSONB so the operator resolves). Each call
    generates fresh parameter bindings, so the helper is safe to invoke
    multiple times in the same query.
    """
    sub = cast(PatentPublication.tags[key], JSONB)
    return sub.has_any(array(values))


def _apply_tab_filters(stmt, tab: str | None):
    """Append tab-specific filters.

    V1 uses a hybrid approach:
    - Score thresholds provide deterministic guardrails
    - Tag checks add LLM-classified nuance where available
    - CPC-based cross-industry detection is deferred (TODO: pgvector kNN)
    """
    # Score thresholds calibrated to current data:
    # max=56.42, avg=45.31, min=34.84 across 47 scored patents.
    if tab is None or tab == "top":
        return stmt.where(PatentPublication.opportunity_score >= 45)

    today = date.today()

    if tab == "expired":
        return stmt.where(
            and_(
                PatentPublication.estimated_expiry_date.isnot(None),
                PatentPublication.estimated_expiry_date < today,
                PatentPublication.opportunity_score >= 40,
            )
        )

    if tab == "revival":
        # Rules: expired/lapsed + score >= 45 + no active family risk.
        # Tags are additive (LLM may flag revival candidates that rules miss).
        tag_check = _tag_contains(
            PatentPublication.tags, "opportunity_tags",
            ["ai_revival_candidate", "public_domain_candidate", "expired_opportunity"]
        )
        rules_check = and_(
            PatentPublication.estimated_expiry_date.isnot(None),
            PatentPublication.estimated_expiry_date < today,
            PatentPublication.opportunity_score >= 45,
            or_(
                PatentPublication.tags.op("->")("risk_flags").is_(None),
                ~_tag_contains(
                    PatentPublication.tags, "risk_flags", ["active_family_risk"]
                ),
            ),
        )
        return stmt.where(or_(rules_check, tag_check))

    if tab == "cross_industry":
        # V1: tag-based only. CPC-based cross-industry deferred.
        # TODO: add pgvector kNN + strict empty industry intersection.
        return stmt.where(
            and_(
                PatentPublication.opportunity_score >= 40,
                _tag_contains(
                    PatentPublication.tags, "opportunity_tags",
                    ["cross_industry_transfer"]
                ),
            )
        )

    if tab == "startup":
        return stmt.where(
            and_(
                PatentPublication.opportunity_score >= 42,
                _tag_contains(
                    PatentPublication.tags, "opportunity_tags",
                    ["startup_opportunity", "low_competition"]
                ),
            )
        )

    if tab == "enterprise":
        return stmt.where(
            and_(
                PatentPublication.opportunity_score >= 42,
                _tag_contains(
                    PatentPublication.tags, "opportunity_tags",
                    ["enterprise_automation", "manufacturing_reuse"]
                ),
            )
        )

    if tab == "sustainability":
        return stmt.where(
            and_(
                PatentPublication.opportunity_score >= 35,
                _tag_contains(
                    PatentPublication.tags, "opportunity_tags",
                    ["sustainability_angle"]
                ),
            )
        )

    if tab == "legal_review":
        # High opportunity but legal uncertainty.
        tag_check = _tag_contains(
            PatentPublication.tags, "risk_flags",
            ["needs_legal_review", "active_family_risk", "unknown_legal_status"]
        )
        rules_check = and_(
            PatentPublication.opportunity_score >= 40,
            PatentPublication.legal_status_confidence == "estimated",
        )
        return stmt.where(or_(rules_check, tag_check))

    return stmt


def _apply_sort(stmt, sort: str):
    if sort == "opportunity_score":
        return stmt.order_by(PatentPublication.opportunity_score.desc().nullslast())
    if sort == "expiring_soon":
        return stmt.order_by(PatentPublication.estimated_expiry_date.asc().nullslast())
    if sort == "newly_published":
        return stmt.order_by(PatentPublication.grant_date.desc().nullslast())
    if sort == "interesting_score":
        return stmt.order_by(PatentPublication.interesting_score.desc().nullslast())
    if sort == "lowest_legal_risk":
        # "confirmed" < "estimated" alphabetically, so ASC puts confirmed
        # first which is exactly the lowest-legal-risk ordering we want.
        return stmt.order_by(
            PatentPublication.legal_status_confidence.asc(),
            PatentPublication.opportunity_score.desc().nullslast(),
        )
    if sort == "strongest_cross_industry":
        # Patents tagged cross_industry_transfer first, then by opp score.
        return stmt.order_by(
            _tag_contains(PatentPublication.tags, "opportunity_tags",
                          ["cross_industry_transfer"]).desc(),
            PatentPublication.opportunity_score.desc().nullslast(),
        )
    return stmt.order_by(PatentPublication.opportunity_score.desc().nullslast())


@router.get("", response_model=PaginatedResponse[OpportunityItem])
async def list_opportunities(
    db: DbSession,
    tab: _Tab | None = Query(default=None),
    industry: str | None = Query(default=None),
    time_horizon: Literal["now", "near_term", "long_term", "unknown"] | None = Query(default=None),
    risk_flag: str | None = Query(default=None),
    opportunity_tag: str | None = Query(default=None),
    legal_confidence: Literal["estimated", "confirmed"] | None = Query(default=None),
    cpc_prefix: str | None = Query(default=None),
    assignee_keyword: str | None = Query(default=None),
    expiry_within_days: int | None = Query(default=None, ge=1, le=20 * 365),
    min_score: float | None = Query(default=None, ge=0.0, le=100.0),
    max_score: float | None = Query(default=None, ge=0.0, le=100.0),
    sort: _Sort = Query(default="opportunity_score"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[OpportunityItem]:
    """List patents ranked by opportunity_score with rich filtering."""
    base = select(PatentPublication).where(
        PatentPublication.opportunity_score.isnot(None)
    )

    base = _apply_tab_filters(base, tab)

    if industry:
        base = base.where(
            _tag_contains(PatentPublication.tags, "industries", [industry])
        )
    if time_horizon:
        # tags ->> 'time_horizon' returns text; compare directly.
        base = base.where(
            PatentPublication.tags["time_horizon"].astext == time_horizon
        )
    if risk_flag:
        base = base.where(
            _tag_contains(PatentPublication.tags, "risk_flags", [risk_flag])
        )
    if opportunity_tag:
        base = base.where(
            _tag_contains(
                PatentPublication.tags, "opportunity_tags", [opportunity_tag]
            )
        )
    if legal_confidence:
        base = base.where(
            PatentPublication.legal_status_confidence == legal_confidence
        )
    if cpc_prefix:
        base = base.where(
            func.jsonb_path_exists(
                PatentPublication.cpc,
                f'$[*] ? (@ starts with "{cpc_prefix}")',
            )
        )
    if assignee_keyword:
        base = base.where(
            text(
                "EXISTS (SELECT 1 FROM jsonb_array_elements_text(assignees) a "
                "WHERE lower(a) LIKE :pat)"
            ).bindparams(pat=f"%{assignee_keyword.lower()}%")
        )
    if expiry_within_days is not None:
        cutoff = date.today() + timedelta(days=expiry_within_days)
        base = base.where(
            and_(
                PatentPublication.estimated_expiry_date.isnot(None),
                PatentPublication.estimated_expiry_date <= cutoff,
            )
        )
    if min_score is not None:
        base = base.where(PatentPublication.opportunity_score >= min_score)
    if max_score is not None:
        base = base.where(PatentPublication.opportunity_score <= max_score)

    # Total count (pre-pagination)
    count_stmt = select(func.count()).select_from(base.subquery())
    total = int((await db.execute(count_stmt)).scalar_one() or 0)

    # Apply sort + pagination
    stmt = _apply_sort(base, sort).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    items = [OpportunityItem.from_patent(p) for p in rows]
    pages = (total + page_size - 1) // page_size

    return PaginatedResponse[OpportunityItem](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# ---------------------------------------------------------------------------
# Tab counts (for tab badges in the UI)
# ---------------------------------------------------------------------------


class TabCounts(BaseModel):
    top: int
    expired: int
    revival: int
    cross_industry: int
    startup: int
    enterprise: int
    sustainability: int
    legal_review: int


@router.get("/tab-counts", response_model=TabCounts)
async def opportunity_tab_counts(db: DbSession) -> TabCounts:
    """Return a count for each opportunity-page tab. Cheap aggregate query."""
    today = date.today()
    base = select(func.count()).select_from(PatentPublication).where(
        PatentPublication.opportunity_score.isnot(None)
    )

    async def _count(stmt) -> int:
        return int((await db.execute(stmt)).scalar_one() or 0)

    # Thresholds calibrated to current data: max=56.42, avg=45.31, min=34.84
    return TabCounts(
        top=await _count(
            base.where(PatentPublication.opportunity_score >= 45)
        ),
        expired=await _count(
            base.where(
                and_(
                    PatentPublication.estimated_expiry_date.isnot(None),
                    PatentPublication.estimated_expiry_date < today,
                    PatentPublication.opportunity_score >= 40,
                )
            )
        ),
        revival=await _count(
            base.where(
                or_(
                    # Tag-based (LLM flagged)
                    _tag_contains(
                        PatentPublication.tags,
                        "opportunity_tags",
                        ["ai_revival_candidate", "public_domain_candidate", "expired_opportunity"],
                    ),
                    # Rules-based (expired + high score + no active family risk)
                    and_(
                        PatentPublication.estimated_expiry_date.isnot(None),
                        PatentPublication.estimated_expiry_date < today,
                        PatentPublication.opportunity_score >= 45,
                        or_(
                            PatentPublication.tags.op("->")("risk_flags").is_(None),
                            ~_tag_contains(
                                PatentPublication.tags, "risk_flags", ["active_family_risk"]
                            ),
                        ),
                    ),
                )
            )
        ),
        cross_industry=await _count(
            base.where(
                and_(
                    PatentPublication.opportunity_score >= 40,
                    _tag_contains(
                        PatentPublication.tags,
                        "opportunity_tags",
                        ["cross_industry_transfer"],
                    ),
                )
            )
        ),
        startup=await _count(
            base.where(
                and_(
                    PatentPublication.opportunity_score >= 42,
                    _tag_contains(
                        PatentPublication.tags,
                        "opportunity_tags",
                        ["startup_opportunity", "low_competition"],
                    ),
                )
            )
        ),
        enterprise=await _count(
            base.where(
                and_(
                    PatentPublication.opportunity_score >= 42,
                    _tag_contains(
                        PatentPublication.tags,
                        "opportunity_tags",
                        ["enterprise_automation", "manufacturing_reuse"],
                    ),
                )
            )
        ),
        sustainability=await _count(
            base.where(
                and_(
                    PatentPublication.opportunity_score >= 35,
                    _tag_contains(
                        PatentPublication.tags,
                        "opportunity_tags",
                        ["sustainability_angle"],
                    ),
                )
            )
        ),
        legal_review=await _count(
            base.where(
                or_(
                    # Tag-based (LLM flagged)
                    _tag_contains(
                        PatentPublication.tags,
                        "risk_flags",
                        ["needs_legal_review", "active_family_risk", "unknown_legal_status"],
                    ),
                    # Rules-based (high opportunity + estimated legal status)
                    and_(
                        PatentPublication.opportunity_score >= 40,
                        PatentPublication.legal_status_confidence == "estimated",
                    ),
                )
            )
        ),
    )
