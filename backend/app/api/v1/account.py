"""
L3 — GDPR account deletion endpoint.

DELETE /api/v1/account/me

Authenticated users can permanently delete their account and all
associated personal data.  Email delivery records and AI run records
are anonymized (user_id / created_by set to NULL) rather than
deleted, preserving the audit trail.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SESSION_COOKIE_NAME, current_user, get_db
from app.config import settings
from app.core.ai_models import AIRun, User
from app.core.billing_models import BillingSubscription
from app.core.subscription_models import EmailDelivery
from app.services.company_suggestions import get_suggested_companies
from app.services.follow_company import add_follow, list_follows, remove_follow

logger = structlog.get_logger(__name__)

router = APIRouter()


class DeleteAccountBody(BaseModel):
    confirm_email: str


@router.delete("/me", status_code=204)
async def delete_account(
    body: DeleteAccountBody,
    user_id: str = Depends(current_user),
    db = Depends(get_db),
):
    """Permanently delete the authenticated user's account.

    Requires the user to confirm their email address as a safety
    check.  Cascade-deletes subscriptions, API keys, billing records,
    magic-link tokens, and exports.  Email delivery and AI run rows
    are anonymized (set to NULL) rather than deleted.
    """
    # ── Fetch user + verify email ─────────────────────────────────
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email and user.email.lower() != body.confirm_email.strip().lower():
        raise HTTPException(status_code=400, detail="Email does not match")

    stripe_customer_id = None
    if user.id:
        billing = (
            await db.execute(
                select(BillingSubscription).where(
                    BillingSubscription.user_id == user.id
                )
            )
        ).scalar_one_or_none()
        if billing and billing.stripe_customer_id:
            stripe_customer_id = billing.stripe_customer_id

    # ── Anonymize audit rows ──────────────────────────────────────
    await db.execute(
        update(EmailDelivery)
        .where(EmailDelivery.user_id == user.id)
        .values(user_id=None)
    )
    await db.execute(
        update(AIRun).where(AIRun.created_by == user.id).values(created_by=None)
    )

    # ── Delete user (FK CASCADE handles subscriptions, api_keys,   ──
    #    billing_subscriptions, magic_link_tokens, exports)         ──
    await db.delete(user)
    await db.commit()

    # ── Log for ops follow-up ─────────────────────────────────────
    log_kwargs = {
        "user_id": user.id,
        "email": user.email,
        "stripe_customer_id": stripe_customer_id,
    }
    if stripe_customer_id:
        logger.warning(
            "Account deleted — Stripe customer NOT deleted (manual ops step)",
            **log_kwargs,
        )
    else:
        logger.info("Account deleted", **log_kwargs)

    # ── Clear session cookie ──────────────────────────────────────
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


# ── Persona ──────────────────────────────────────────────────


class PersonaSetRequest(BaseModel):
    persona: str  # "operator" | "investor" | "curious"


class PersonaResponse(BaseModel):
    persona: str | None


@router.put("/persona", response_model=PersonaResponse)
async def set_persona(
    request: PersonaSetRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if request.persona not in ("operator", "investor", "curious"):
        raise HTTPException(422, "persona must be operator, investor, or curious")
    user.persona = request.persona
    await db.commit()
    return PersonaResponse(persona=user.persona)


class EmailPreferencesResponse(BaseModel):
    weekly_briefing_enabled: bool = True
    instant_alerts_enabled: bool = False


class EmailPreferencesUpdate(BaseModel):
    weekly_briefing_enabled: bool | None = None
    instant_alerts_enabled: bool | None = None


@router.get("/email-preferences", response_model=EmailPreferencesResponse)
async def get_email_preferences(
    user: User = Depends(current_user),
) -> EmailPreferencesResponse:
    prefs = user.preferences or {}
    return EmailPreferencesResponse(
        weekly_briefing_enabled=prefs.get("weekly_briefing_enabled", True),
        instant_alerts_enabled=prefs.get("instant_alerts_enabled", False),
    )


@router.put("/email-preferences", response_model=EmailPreferencesResponse)
async def update_email_preferences(
    body: EmailPreferencesUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> EmailPreferencesResponse:
    prefs = dict(user.preferences or {})
    if body.weekly_briefing_enabled is not None:
        prefs["weekly_briefing_enabled"] = body.weekly_briefing_enabled
    if body.instant_alerts_enabled is not None:
        prefs["instant_alerts_enabled"] = body.instant_alerts_enabled
    user.preferences = prefs
    await db.commit()
    return EmailPreferencesResponse(
        weekly_briefing_enabled=prefs.get("weekly_briefing_enabled", True),
        instant_alerts_enabled=prefs.get("instant_alerts_enabled", False),
    )


# ── Company follows ─────────────────────────────────────────


class CompanyFollowRequest(BaseModel):
    company_name: str


class CompanyFollowResponse(BaseModel):
    company_normalized_name: str
    display_name: str


@router.post("/companies", status_code=201, response_model=CompanyFollowResponse)
async def follow_company(
    request: CompanyFollowRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    follow = await add_follow(db, user.id, request.company_name)
    return CompanyFollowResponse(
        company_normalized_name=follow.company_normalized_name,
        display_name=follow.display_name,
    )


@router.delete("/companies/{normalized_name}", status_code=204)
async def unfollow_company(
    normalized_name: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await remove_follow(db, user.id, normalized_name)
    if not deleted:
        raise HTTPException(404, "Company not found in your follows")


@router.get("/companies", response_model=list[CompanyFollowResponse])
async def get_company_follows(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    follows = await list_follows(db, user.id)
    return [
        CompanyFollowResponse(
            company_normalized_name=f.company_normalized_name,
            display_name=f.display_name,
        )
        for f in follows
    ]


# ── Company suggestions ────────────────────────────────────


@router.get("/companies/suggested")
async def get_suggested_companies_endpoint(
    persona: str = "curious",
    db: AsyncSession = Depends(get_db),
):
    """Return persona-biased company suggestions with patent counts."""
    if persona not in ("operator", "investor", "curious"):
        persona = "curious"
    return await get_suggested_companies(db, persona=persona)


# ── Phase 4 PR 3: Usage endpoint ───────────────────────────────


class FeatureUsage(BaseModel):
    used: int
    limit: int | None = None
    remaining: int | None = None
    unlimited: bool = False
    period: str | None = None  # "daily", "monthly", "yearly", or None


class UsageResponse(BaseModel):
    tier: str
    features: dict[str, FeatureUsage]
    renews_at: str | None = None


@router.get("/usage", response_model=UsageResponse)
async def get_account_usage(
    user_id: str = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated usage across all gated features.

    Counts themes (topic subscriptions), companies followed, and chat
    messages from Redis. Views and search are unlimited on all tiers.
    """
    from datetime import date

    import redis.asyncio as aioredis
    from sqlalchemy import func, select as sa_select

    from app.core.ai_models import User, UserCompanyFollow
    from app.core.billing_models import BillingSubscription
    from app.core.subscription_models import TopicSubscription as _TopicSubscription

    # ── User + tier ──────────────────────────────────────────────
    user = (await db.execute(sa_select(User).where(User.id == user_id))).scalar_one_or_none()
    tier = user.tier if user else "free"

    # ── Chat quota from Redis ────────────────────────────────────
    chat_used = 0
    chat_limit: int | None = 50  # basic default
    chat_unlimited = False

    if tier == "free":
        chat_limit = settings.chat_quota_free
    elif tier == "basic":
        chat_limit = settings.chat_quota_basic
    else:
        chat_unlimited = True
        chat_limit = None

    try:
        redis_client = aioredis.Redis.from_url(settings.redis_url, decode_responses=True)
        today_str = date.today().isoformat()
        key = f"chat:quota:{user_id}:{today_str}"
        chat_used_raw = await redis_client.get(key)
        chat_used = int(chat_used_raw) if chat_used_raw else 0
        await redis_client.close()
    except Exception:
        chat_used = 0

    chat_remaining: int | None = None
    if chat_limit is not None:
        chat_remaining = max(0, chat_limit - chat_used)

    # ── Themes (topic subscriptions) ─────────────────────────────
    themes_used_raw = await db.execute(
        sa_select(func.count()).select_from(_TopicSubscription).where(
            _TopicSubscription.user_id == user_id
        )
    )
    themes_used = themes_used_raw.scalar() or 0
    themes_limit = 1 if tier == "free" else None
    themes_unlimited = tier != "free"
    themes_remaining: int | None = None
    if themes_limit is not None:
        themes_remaining = max(0, themes_limit - themes_used)

    # ── Companies followed ───────────────────────────────────────
    companies_used_raw = await db.execute(
        sa_select(func.count()).select_from(UserCompanyFollow).where(
            UserCompanyFollow.user_id == user_id
        )
    )
    companies_used = companies_used_raw.scalar() or 0
    companies_limit = 3 if tier == "free" else None
    companies_unlimited = tier != "free"
    companies_remaining: int | None = None
    if companies_limit is not None:
        companies_remaining = max(0, companies_limit - companies_used)

    # ── Renews_at from billing ───────────────────────────────────
    renews_at: str | None = None
    billing_sub = (await db.execute(
        sa_select(BillingSubscription).where(BillingSubscription.user_id == user_id)
    )).scalar_one_or_none()
    if billing_sub and billing_sub.current_period_end:
        renews_at = billing_sub.current_period_end.isoformat()

    return {
        "tier": tier,
        "features": {
            "views": FeatureUsage(used=0, unlimited=True, period=None),
            "search": FeatureUsage(used=0, unlimited=True, period=None),
            "themes": FeatureUsage(
                used=themes_used,
                limit=themes_limit,
                remaining=themes_remaining,
                unlimited=themes_unlimited,
            ),
            "companies": FeatureUsage(
                used=companies_used,
                limit=companies_limit,
                remaining=companies_remaining,
                unlimited=companies_unlimited,
            ),
            "chat": FeatureUsage(
                used=chat_used,
                limit=chat_limit,
                remaining=chat_remaining,
                unlimited=chat_unlimited,
                period="daily",
            ),
        },
        "renews_at": renews_at,
    }
