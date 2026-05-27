"""
Per-tier quota enforcement (Sprint 7).

Centralized TIER_LIMITS dict. All quota checks are async and accept
a session parameter (S6-9 pattern). HTTP 402 on quota exceeded.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import User
from app.core.subscription_models import EmailDelivery, TopicSubscription

# ── tier limits ──────────────────────────────────────────────────────

TIER_LIMITS: dict[str, dict[str, int | None]] = {
    "free": {
        "max_topics": 1,
        "max_alerts_per_week": 5,
        "csv_exports": 0,
        "pdf_reports": 0,
        "api_access": 0,
    },
    "basic": {
        "max_topics": None,  # unlimited
        "max_alerts_per_week": None,
        "csv_exports": None,
        "pdf_reports": 0,
        "api_access": 0,
    },
    "lifetime": {
        "max_topics": None,
        "max_alerts_per_week": None,
        "csv_exports": None,
        "pdf_reports": None,
        "api_access": 0,
    },
    "enterprise": {
        "max_topics": None,
        "max_alerts_per_week": None,
        "csv_exports": None,
        "pdf_reports": None,
        "api_access": None,
    },
}


# ── quota checks ─────────────────────────────────────────────────────


async def check_topic_quota(
    user_id: str,
    session: AsyncSession,
) -> None:
    """Raise 402 if the user has exceeded their topic subscription limit."""
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    tier = user.tier if user else "free"
    max_topics = TIER_LIMITS.get(tier, {}).get("max_topics")
    if max_topics is None:
        return

    count = (await session.execute(
        select(TopicSubscription).where(TopicSubscription.user_id == user_id)
    )).scalars().all()
    existing = len(count)

    if existing >= max_topics:
        _next = _next_tier_with("max_topics", tier)
        raise HTTPException(
            status_code=402,
            detail=f"Topic limit reached ({max_topics}). "
            f"Upgrade to {_next} for unlimited topics.",
        )


async def check_alert_quota(
    session: AsyncSession,
    user_id: str,
) -> bool:
    """Return True if user can receive another alert this week."""
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    tier = user.tier if user else "free"
    max_alerts = TIER_LIMITS.get(tier, {}).get("max_alerts_per_week")
    if max_alerts is None:
        return True

    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    count = (await session.execute(
        select(EmailDelivery).where(
            EmailDelivery.user_id == user_id,
            EmailDelivery.email_type == "instant_alert",
            EmailDelivery.sent_at >= one_week_ago,
        )
    )).scalars().all()

    return len(count) < max_alerts


def require_tier(*allowed_tiers: str):
    """FastAPI dependency: 402 if user.tier not in allowed_tiers."""

    async def _check(
        user_id: str = Depends(_get_user_id),
        session: AsyncSession = Depends(_get_session),
    ):
        user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        tier = user.tier if user else "free"
        if tier not in allowed_tiers:
            raise HTTPException(
                status_code=402,
                detail=f"This feature requires one of: {', '.join(allowed_tiers)}. "
                f"Your current tier is {tier}. Upgrade to access this.",
            )

    return _check


# ── helpers ──────────────────────────────────────────────────────────


def _next_tier_with(feature: str, current_tier: str) -> str:
    """Return the name of the closest higher tier that unlocks a feature."""
    order = ["free", "basic", "lifetime", "enterprise"]
    idx = order.index(current_tier) if current_tier in order else 0
    for t in order[idx + 1:]:
        if TIER_LIMITS.get(t, {}).get(feature) not in (0, None):
            return t
    return order[-1]


async def _get_user_id():
    """Lazy import to work as FastAPI Depends."""
    from app.api.deps import current_user
    return await current_user()


async def _get_session():
    from app.api.deps import get_db
    async for s in get_db():
        return s
