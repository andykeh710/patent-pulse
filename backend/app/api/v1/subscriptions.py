"""Sprint 6 — Subscription management endpoints."""

from __future__ import annotations

import hashlib
import hmac
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import current_user, get_db
from app.config import settings
from app.core.subscription_models import TopicSubscription

router = APIRouter()


# ── schemas ──────────────────────────────────────────────────────────


class SubscriptionCreate(BaseModel):
    theme_id: UUID
    mode: str  # "instant_alert" | "weekly_digest"
    min_score: float | None = None


class SubscriptionUpdate(BaseModel):
    mode: str | None = None
    min_score: float | None = None
    paused: bool | None = None


class SubscriptionResponse(BaseModel):
    id: UUID
    user_id: str
    theme_id: UUID
    mode: str
    min_score: float | None = None
    paused: bool = False
    last_delivered_at: str | None = None

    @classmethod
    def from_row(cls, row: TopicSubscription) -> SubscriptionResponse:
        return cls(
            id=row.id,
            user_id=row.user_id,
            theme_id=row.theme_id,
            mode=row.mode,
            min_score=row.min_score,
            paused=row.paused,
            last_delivered_at=(
                row.last_delivered_at.isoformat() if row.last_delivered_at else None
            ),
        )


# ── helpers ──────────────────────────────────────────────────────────


ALLOWED_MODES = {"instant_alert", "weekly_digest"}


def _sign_subscription_id(subscription_id: UUID) -> str:
    """HMAC-SHA256 sign a subscription_id for 1-click unsubscribe."""
    return hmac.new(
        settings.auth_secret_key.encode(),
        str(subscription_id).encode(),
        hashlib.sha256,
    ).hexdigest()


def _verify_unsubscribe_token(subscription_id: UUID, token: str) -> bool:
    """Constant-time comparison of HMAC signature."""
    expected = _sign_subscription_id(subscription_id)
    return hmac.compare_digest(expected, token)


# ── endpoints ────────────────────────────────────────────────────────


@router.get("", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    """List current user's subscriptions."""
    result = await db.execute(select(TopicSubscription).where(TopicSubscription.user_id == user_id))
    rows = result.scalars().all()
    return [SubscriptionResponse.from_row(r) for r in rows]


@router.post("", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    body: SubscriptionCreate,
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    """Create a subscription to a theme."""
    from app.quotas.limits import check_topic_quota

    await check_topic_quota(user_id, db)

    if body.mode not in ALLOWED_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {body.mode}")

    # Ownership: user can only subscribe to themes (themes endpoint validates
    # theme_id exists; here we trust the caller has a valid theme_id).
    # Check duplicate.
    existing = await db.execute(
        select(TopicSubscription).where(
            TopicSubscription.user_id == user_id,
            TopicSubscription.theme_id == body.theme_id,
            TopicSubscription.mode == body.mode,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="Already subscribed to this theme with this mode"
        )

    sub = TopicSubscription(
        user_id=user_id,
        theme_id=body.theme_id,
        mode=body.mode,
        min_score=body.min_score,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return SubscriptionResponse.from_row(sub)


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: UUID,
    body: SubscriptionUpdate,
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    """Update mode, min_score, or paused state."""
    result = await db.execute(
        select(TopicSubscription).where(
            TopicSubscription.id == subscription_id,
            TopicSubscription.user_id == user_id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if body.mode is not None:
        if body.mode not in ALLOWED_MODES:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {body.mode}")
        sub.mode = body.mode
    if body.min_score is not None:
        sub.min_score = body.min_score
    if body.paused is not None:
        sub.paused = body.paused

    await db.commit()
    await db.refresh(sub)
    return SubscriptionResponse.from_row(sub)


@router.delete("/{subscription_id}", status_code=204)
async def delete_subscription(
    subscription_id: UUID,
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    """Delete a subscription (authenticated)."""
    result = await db.execute(
        select(TopicSubscription).where(
            TopicSubscription.id == subscription_id,
            TopicSubscription.user_id == user_id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    await db.delete(sub)
    await db.commit()


@router.get("/unsubscribe")
async def unsubscribe(
    subscription: UUID,
    token: str,
    db=Depends(get_db),
):
    """Public 1-click unsubscribe from email footer. Pauses subscription."""
    if not _verify_unsubscribe_token(subscription, token):
        raise HTTPException(status_code=400, detail="Invalid unsubscribe link")

    result = await db.execute(select(TopicSubscription).where(TopicSubscription.id == subscription))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    sub.paused = True
    await db.commit()

    return {"ok": True, "message": "You have been unsubscribed."}
