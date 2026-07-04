"""V3.1 — Preference Center API.

Endpoints:
    GET  /api/v1/me/preferences
    PATCH /api/v1/me/preferences
    POST /api/v1/me/feed/interactions
    POST /api/v1/me/feed/hide
    POST /api/v1/me/feed/feedback
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import DbSession, current_user
from app.core.ai_models import User as UserModel
from app.core.ai_models import UserCompanyFollow
from app.core.schemas import (
    FeedFeedbackRequest,
    FeedInteractionRequest,
    HideFeedItemRequest,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from app.core.subscription_models import TopicSubscription

router = APIRouter(prefix="/me", tags=["preferences"])


# ── Preferences ───────────────────────────────────────────────────────


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    db: DbSession,
    user_id: str = Depends(current_user),
):
    """Return the current user's preference state."""
    from sqlalchemy import func, select

    # SavedSearch is defined in the saved_searches API module
    from app.api.v1.saved_searches import SavedSearch as SavedSearchModel
    from app.core.theme_models import WatchlistItem

    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    topic_count = await db.scalar(
        select(func.count(TopicSubscription.id)).where(TopicSubscription.user_id == user_id)
    )
    company_count = await db.scalar(
        select(func.count(UserCompanyFollow.user_id)).where(UserCompanyFollow.user_id == user_id)
    )
    patent_count = await db.scalar(
        select(func.count(WatchlistItem.id)).where(WatchlistItem.user_id == user_id)
    )
    search_count = await db.scalar(
        select(func.count(SavedSearchModel.id)).where(SavedSearchModel.user_id == user_id)
    )

    return UserPreferencesResponse(
        persona=user.persona,
        use_case=getattr(user, "use_case", None),
        industry_focus=user.industry_focus,
        interests_freetext=user.interests_freetext,
        digest_frequency=getattr(user, "digest_frequency", "weekly"),
        digest_topics_only=bool(getattr(user, "digest_topics_only", False)),
        digest_min_opp_score=float(getattr(user, "digest_min_opp_score", 0.0)),
        followed_topic_count=topic_count or 0,
        followed_company_count=company_count or 0,
        saved_patent_count=patent_count or 0,
        saved_search_count=search_count or 0,
    )


@router.patch("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    body: UserPreferencesUpdate,
    db: DbSession,
    user_id: str = Depends(current_user),
):
    """Update the current user's preferences. All fields optional."""
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return await get_preferences(db, user_id)


# ── Feed Interactions ─────────────────────────────────────────────────


@router.post("/feed/interactions", status_code=201)
async def create_feed_interaction(
    body: FeedInteractionRequest,
    db: DbSession,
    user_id: str = Depends(current_user),
):
    """Record a feed interaction event (view, click, save, etc.)."""
    from sqlalchemy import text

    await db.execute(
        text(
            """INSERT INTO feed_interactions
               (user_id, object_type, object_id, interaction_type)
               VALUES (:uid, :otype, :oid, :itype)"""
        ),
        {
            "uid": user_id,
            "otype": body.object_type,
            "oid": body.object_id,
            "itype": body.interaction_type,
        },
    )
    await db.commit()
    return {"ok": True}


# ── Hide / Feedback ───────────────────────────────────────────────────


@router.post("/feed/hide", status_code=201)
async def hide_feed_item(
    body: HideFeedItemRequest,
    db: DbSession,
    user_id: str = Depends(current_user),
):
    """Hide a feed item. Persisted to hidden_feed_items."""
    from sqlalchemy import text

    await db.execute(
        text(
            """INSERT INTO hidden_feed_items (user_id, object_type, object_id)
               VALUES (:uid, :otype, :oid)
               ON CONFLICT (user_id, object_type, object_id) DO NOTHING"""
        ),
        {"uid": user_id, "otype": body.object_type, "oid": body.object_id},
    )
    await db.commit()
    return {"ok": True}


@router.post("/feed/feedback", status_code=201)
async def submit_feedback(
    body: FeedFeedbackRequest,
    db: DbSession,
    user_id: str = Depends(current_user),
):
    """Submit useful/not_useful feedback. Stores as a feed_interaction row."""
    from sqlalchemy import text

    itype = f"marked_{body.feedback_type}"
    await db.execute(
        text(
            """INSERT INTO feed_interactions
               (user_id, object_type, object_id, interaction_type)
               VALUES (:uid, :otype, :oid, :itype)"""
        ),
        {
            "uid": user_id,
            "otype": body.object_type,
            "oid": body.object_id,
            "itype": itype,
        },
    )
    await db.commit()
    return {"ok": True}
