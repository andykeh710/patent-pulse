"""Sprint 7 — Billing API endpoints (Stripe Checkout + Webhooks)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import current_user, get_db
from app.billing.stripe_client import (
    create_checkout_session,
    create_billing_portal_session,
    verify_webhook_signature,
)
from app.config import settings
from app.core.ai_models import User
from app.core.billing_models import BillingSubscription
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


# ── schemas ──────────────────────────────────────────────────────────

VALID_TIERS = {"basic", "lifetime", "enterprise"}


class CheckoutRequest(BaseModel):
    tier: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    created_at: datetime | None = None


# ── endpoints ────────────────────────────────────────────────────────


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    user_id: str = Depends(current_user),
    db=Depends(get_db),
):
    """Return the current user's billing subscription. Never 404s."""
    from sqlalchemy import select

    existing = (await db.execute(
        select(BillingSubscription).where(BillingSubscription.user_id == user_id)
    )).scalar_one_or_none()

    user = (await db.execute(
        select(User).where(User.id == user_id)
    )).scalar_one_or_none()

    tier = user.tier if user else "free"

    if existing:
        return SubscriptionResponse(
            tier=existing.tier,
            status=existing.status,
            stripe_customer_id=existing.stripe_customer_id,
            stripe_subscription_id=existing.stripe_subscription_id,
            current_period_end=existing.current_period_end,
            cancel_at_period_end=existing.cancel_at_period_end,
            created_at=existing.created_at,
        )

    return SubscriptionResponse(tier=tier, status="active")


@router.post("/checkout-session", response_model=CheckoutResponse)
async def start_checkout(
    body: CheckoutRequest,
    user_id: str = Depends(current_user),
    db=Depends(get_db),
    request: Request = None,
):
    if body.tier not in VALID_TIERS:
        raise HTTPException(status_code=422, detail=f"Invalid tier: {body.tier}")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()

    existing = (await db.execute(
        select(BillingSubscription).where(BillingSubscription.user_id == user_id)
    )).scalar_one_or_none()

    customer_id = existing.stripe_customer_id if existing else None
    base_url = str(request.base_url).rstrip("/") if request else settings.magic_link_base_url

    result = create_checkout_session(
        user_id=user_id,
        user_email=user.email,
        tier=body.tier,
        stripe_customer_id=customer_id,
        base_url=base_url,
    )
    return CheckoutResponse(checkout_url=result["url"])


@router.post("/portal-session", response_model=PortalResponse)
async def start_portal(
    user_id: str = Depends(current_user),
    db=Depends(get_db),
    request: Request = None,
):
    existing = (await db.execute(
        select(BillingSubscription).where(BillingSubscription.user_id == user_id)
    )).scalar_one_or_none()

    if not existing or not existing.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer found")

    base_url = str(request.base_url).rstrip("/") if request else settings.magic_link_base_url

    result = create_billing_portal_session(
        stripe_customer_id=existing.stripe_customer_id,
        base_url=base_url,
    )
    return PortalResponse(portal_url=result["url"])


@router.post("/webhook")
@limiter.exempt
async def handle_webhook(
    request: Request,
    db=Depends(get_db),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = verify_webhook_signature(payload, sig_header)
    except Exception as e:
        logger.warning("Invalid Stripe webhook signature: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info("Stripe webhook: %s", event_type)

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(db, data)
        elif event_type == "invoice.payment_succeeded":
            await _handle_invoice_paid(db, data)
        elif event_type == "invoice.payment_failed":
            await _handle_invoice_failed(db, data)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(db, data)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(db, data)
    except Exception as e:
        logger.error("Webhook handler error for %s: %s", event_type, e)
        raise HTTPException(status_code=500, detail="Handler error")

    return {"status": "ok"}


# ── webhook handlers ─────────────────────────────────────────────────


async def _handle_checkout_completed(db, session_data: dict) -> None:
    user_id = session_data.get("metadata", {}).get("user_id", "")
    if not user_id:
        return

    tier = session_data.get("metadata", {}).get("tier", "free")
    customer_id = session_data.get("customer")
    subscription_id = session_data.get("subscription")
    payment_intent_id = session_data.get("payment_intent")
    mode = session_data.get("mode")

    existing = (await db.execute(
        select(BillingSubscription).where(BillingSubscription.user_id == user_id)
    )).scalar_one_or_none()

    row = existing or BillingSubscription(user_id=user_id)
    row.tier = tier
    row.stripe_customer_id = customer_id
    row.status = "active"

    if mode == "subscription":
        row.stripe_subscription_id = subscription_id
        row.stripe_payment_intent_id = None
    else:  # payment (Lifetime)
        row.stripe_subscription_id = None
        row.stripe_payment_intent_id = payment_intent_id

    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    await db.commit()

    # Update user.tier denormalized field.
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user:
        user.tier = tier
        await db.commit()


async def _handle_invoice_paid(db, invoice: dict) -> None:
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return
    existing = (await db.execute(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
    )).scalar_one_or_none()
    if existing:
        existing.status = "active"
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()


async def _handle_invoice_failed(db, invoice: dict) -> None:
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return
    existing = (await db.execute(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == subscription_id
        )
    )).scalar_one_or_none()
    if existing:
        existing.status = "past_due"
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()


async def _handle_subscription_deleted(db, subscription: dict) -> None:
    sub_id = subscription.get("id")
    if not sub_id:
        return
    existing = (await db.execute(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == sub_id
        )
    )).scalar_one_or_none()
    if existing:
        existing.tier = "free"
        existing.status = "canceled"
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()

        user = (await db.execute(select(User).where(User.id == existing.user_id))).scalar_one_or_none()
        if user:
            user.tier = "free"
            await db.commit()


async def _handle_subscription_updated(db, subscription: dict) -> None:
    sub_id = subscription.get("id")
    if not sub_id:
        return
    existing = (await db.execute(
        select(BillingSubscription).where(
            BillingSubscription.stripe_subscription_id == sub_id
        )
    )).scalar_one_or_none()
    if existing and subscription.get("status") == "active":
        existing.status = "active"
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
