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
from app.core.ai_models import AIRun, User
from app.core.billing_models import BillingSubscription
from app.core.subscription_models import EmailDelivery
from app.services.company_suggestions import get_suggested_companies
from app.services.follow_company import add_follow, list_follows, remove_follow

logger = structlog.get_logger(__name__)

router = APIRouter()


class DeleteAccountBody(BaseModel):
    confirm_email: str


async def _get_user_or_404(db: AsyncSession, user_id: str) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


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
    user_id: str = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if request.persona not in ("operator", "investor", "curious"):
        raise HTTPException(422, "persona must be operator, investor, or curious")
    user = await _get_user_or_404(db, user_id)
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
    user_id: str = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> EmailPreferencesResponse:
    user = await _get_user_or_404(db, user_id)
    prefs = user.preferences or {}
    return EmailPreferencesResponse(
        weekly_briefing_enabled=prefs.get("weekly_briefing_enabled", True),
        instant_alerts_enabled=prefs.get("instant_alerts_enabled", False),
    )


@router.put("/email-preferences", response_model=EmailPreferencesResponse)
async def update_email_preferences(
    body: EmailPreferencesUpdate,
    user_id: str = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> EmailPreferencesResponse:
    user = await _get_user_or_404(db, user_id)
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
    user_id: str = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_or_404(db, user_id)
    follow = await add_follow(db, user_id, request.company_name)
    return CompanyFollowResponse(
        company_normalized_name=follow.company_normalized_name,
        display_name=follow.display_name,
    )


@router.delete("/companies/{normalized_name}", status_code=204)
async def unfollow_company(
    normalized_name: str,
    user_id: str = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_or_404(db, user_id)
    deleted = await remove_follow(db, user_id, normalized_name)
    if not deleted:
        raise HTTPException(404, "Company not found in your follows")


@router.get("/companies", response_model=list[CompanyFollowResponse])
async def get_company_follows(
    user_id: str = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_or_404(db, user_id)
    follows = await list_follows(db, user_id)
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
