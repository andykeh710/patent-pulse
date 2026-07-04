"""Retention & Feedback API — Sprint 7.

Endpoint inventory:
  POST   /api/v1/feedback              — submit feedback
  GET    /api/v1/feedback/admin        — admin view (requires admin)
  GET    /api/v1/activation-state      — current user activation state
  POST   /api/v1/alert-intent          — capture alert intent
  GET    /api/v1/admin/retention       — retention summary (requires admin)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.api.deps import DbSession, current_user

router = APIRouter(tags=["retention-feedback"])


# -- Models ------------------------------------------------------------------


class FeedbackCreate(BaseModel):
    route: str  # e.g. /today, /search, /patents/{id}
    surface: str  # today | search | patent-detail | companies | expiry | watchlist
    rating: str = Field(description="useful | not_useful | data_issue | feature_request")
    message: str | None = None
    object_type: str | None = None
    object_id: str | None = None


class FeedbackResponse(BaseModel):
    id: str
    user_id: str | None
    route: str
    surface: str
    rating: str
    message: str | None
    created_at: str


class ActivationState(BaseModel):
    user_id: str
    has_opened_today: bool
    saved_patent_count: int
    saved_search_count: int
    followed_company_count: int
    patent_detail_views: int
    feedback_count: int
    activated: bool
    strongly_activated: bool
    missing_steps: list[str]


class AlertIntentCreate(BaseModel):
    alert_type: str = Field(description="saved_search_changes | company_expiry | expiry_window")
    query_or_filter_json: dict | None = None
    frequency: str = "weekly"


class RetentionSummary(BaseModel):
    total_users: int
    activated_users: int
    strongly_activated_users: int
    today_views: int
    saved_patents: int
    saved_searches: int
    feedback_count: int
    top_feedback_surfaces: list[str]


# -- Feedback endpoints ------------------------------------------------------


@router.post("/feedback", status_code=201)
async def submit_feedback(
    body: FeedbackCreate,
    db: DbSession,
    user_id: str = Depends(current_user),
) -> dict:
    """Submit feedback from any surface."""
    feedback_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            "INSERT INTO feedback (id, user_id, route, surface, rating, message, object_type, object_id, created_at) "
            "VALUES (:id, :uid, :route, :surface, :rating, :message, :otype, :oid, :now)"
        ),
        {
            "id": feedback_id,
            "uid": user_id,
            "route": body.route,
            "surface": body.surface,
            "rating": body.rating,
            "message": body.message,
            "otype": body.object_type,
            "oid": body.object_id,
            "now": now,
        },
    )
    await db.commit()
    return {"id": str(feedback_id), "status": "submitted"}


@router.get("/feedback/admin", response_model=list[FeedbackResponse])
async def list_feedback(
    db: DbSession,
    user_id: str = Depends(current_user),
    limit: int = 50,
    surface: str | None = None,
) -> list[FeedbackResponse]:
    """Admin view of recent feedback. Requires admin user."""

    # Verify admin
    result = await db.execute(text("SELECT is_admin FROM users WHERE id = :uid"), {"uid": user_id})
    row = result.one_or_none()
    if not row or not row[0]:
        raise HTTPException(status_code=403, detail="Admin access required")

    where = "WHERE 1=1"
    params: dict = {"limit": limit}
    if surface:
        where += " AND surface = :surface"
        params["surface"] = surface

    rows = (
        await db.execute(
            text(f"SELECT * FROM feedback {where} ORDER BY created_at DESC LIMIT :limit"),
            params,
        )
    ).fetchall()

    return [
        FeedbackResponse(
            id=str(r.id),
            user_id=r.user_id,
            route=r.route,
            surface=r.surface,
            rating=r.rating,
            message=r.message,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


# -- Activation state ---------------------------------------------------------


@router.get("/activation-state", response_model=ActivationState)
async def activation_state(
    db: DbSession,
    user_id: str = Depends(current_user),
) -> ActivationState:
    """Return the activation state for the current user."""
    params = {"uid": user_id}

    # Today views
    today_row = (
        await db.execute(
            text("SELECT last_today_seen_at, previous_today_seen_at FROM users WHERE id = :uid"),
            params,
        )
    ).one_or_none()
    has_today = today_row and today_row[0] is not None

    # Saved patents
    patent_row = (
        await db.execute(
            text("SELECT COUNT(*) FROM watchlist WHERE user_id = :uid"),
            params,
        )
    ).scalar()

    # Saved searches
    search_row = (
        await db.execute(
            text("SELECT COUNT(*) FROM saved_searches WHERE user_id = :uid"),
            params,
        )
    ).scalar()

    # Followed companies
    company_row = (
        await db.execute(
            text("SELECT COUNT(*) FROM user_company_follows WHERE user_id = :uid"),
            params,
        )
    ).scalar()

    # Feedback
    feedback_row = (
        await db.execute(
            text("SELECT COUNT(*) FROM feedback WHERE user_id = :uid"),
            params,
        )
    ).scalar()

    saved_patents = int(patent_row or 0)
    saved_searches = int(search_row or 0)
    followed_companies = int(company_row or 0)
    feedback_count = int(feedback_row or 0)

    # Activation criteria: 2+ of the following
    activation_steps = 0
    missing: list[str] = []
    if has_today:
        activation_steps += 1
    else:
        missing.append("Open your Today briefing")
    if saved_patents > 0:
        activation_steps += 1
    else:
        missing.append("Save a patent")
    if saved_searches > 0:
        activation_steps += 1
    else:
        missing.append("Save a search")
    if followed_companies > 0:
        activation_steps += 1
    else:
        missing.append("Follow a company")
    if feedback_count > 0:
        activation_steps += 1
    else:
        missing.append("Submit feedback")

    activated = activation_steps >= 2
    strongly_activated = activation_steps >= 4

    return ActivationState(
        user_id=user_id,
        has_opened_today=has_today,
        saved_patent_count=saved_patents,
        saved_search_count=saved_searches,
        followed_company_count=followed_companies,
        patent_detail_views=0,  # not tracked yet
        feedback_count=feedback_count,
        activated=activated,
        strongly_activated=strongly_activated,
        missing_steps=missing if not activated else [],
    )


# -- Alert intent ------------------------------------------------------------


@router.post("/alert-intent", status_code=201)
async def create_alert_intent(
    body: AlertIntentCreate,
    db: DbSession,
    user_id: str = Depends(current_user),
) -> dict:
    """Capture alert intent. Delivery is not yet active — this stores
    the user's preference for when the alert infrastructure is ready.
    """
    from datetime import datetime, timezone

    intent_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            "INSERT INTO alert_intents (id, user_id, alert_type, query_or_filter_json, frequency, created_at) "
            "VALUES (:id, :uid, :atype, CAST(:qf AS jsonb), :freq, :now)"
        ),
        {
            "id": intent_id,
            "uid": user_id,
            "atype": body.alert_type,
            "qf": body.query_or_filter_json or "null",
            "freq": body.frequency,
            "now": now,
        },
    )
    await db.commit()
    return {
        "id": str(intent_id),
        "status": "intent_captured",
        "note": "Alert delivery will be available in a future update.",
    }


# -- Retention summary (admin) -----------------------------------------------


@router.get("/admin/retention", response_model=RetentionSummary)
async def retention_summary(
    db: DbSession,
    user_id: str = Depends(current_user),
) -> RetentionSummary:
    """Admin retention summary. Requires admin user."""
    result = await db.execute(text("SELECT is_admin FROM users WHERE id = :uid"), {"uid": user_id})
    row = result.one_or_none()
    if not row or not row[0]:
        raise HTTPException(status_code=403, detail="Admin access required")

    total = (await db.execute(text("SELECT COUNT(*) FROM users"))).scalar() or 0
    today_v = (
        await db.execute(text("SELECT COUNT(*) FROM users WHERE last_today_seen_at IS NOT NULL"))
    ).scalar() or 0
    saved_p = (
        await db.execute(text("SELECT COUNT(DISTINCT user_id) FROM watchlist"))
    ).scalar() or 0
    saved_s = (
        await db.execute(text("SELECT COUNT(DISTINCT user_id) FROM saved_searches"))
    ).scalar() or 0
    feedback_c = (await db.execute(text("SELECT COUNT(*) FROM feedback"))).scalar() or 0

    surfaces = (
        await db.execute(
            text(
                "SELECT surface, COUNT(*) as cnt FROM feedback GROUP BY surface ORDER BY cnt DESC LIMIT 5"
            )
        )
    ).fetchall()

    return RetentionSummary(
        total_users=int(total),
        activated_users=0,  # requires cross-table activation calc — deferred
        strongly_activated_users=0,
        today_views=int(today_v),
        saved_patents=int(saved_p),
        saved_searches=int(saved_s),
        feedback_count=int(feedback_c),
        top_feedback_surfaces=[r.surface for r in surfaces],
    )
