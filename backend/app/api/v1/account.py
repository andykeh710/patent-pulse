"""
L3 — GDPR account deletion endpoint.

DELETE /api/v1/account/me

Authenticated users can permanently delete their account and all
associated personal data.  Email delivery records and AI run records
are anonymized (user_id / created_by set to NULL) rather than
deleted, preserving the audit trail.
"""

from __future__ import annotations

import logging

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select, update

from app.api.deps import current_user, get_db, SESSION_COOKIE_NAME
from app.core.ai_models import AIRun, User
from app.core.billing_models import BillingSubscription
from app.core.subscription_models import EmailDelivery

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
