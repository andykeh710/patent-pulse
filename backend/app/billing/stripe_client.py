"""Stripe client wrapper (Sprint 7). TEST MODE ONLY per AGENTS.md."""

from __future__ import annotations

import logging

import stripe

from app.config import settings

logger = logging.getLogger(__name__)

TIER_TO_PRICE_ID = {
    "basic": settings.stripe_price_id_basic,
    "lifetime": settings.stripe_price_id_lifetime,
    "enterprise": settings.stripe_price_id_enterprise,
}

RECURRING_TIERS = {"basic", "enterprise"}
ONE_TIME_TIERS = {"lifetime"}


def _ensure_api_key() -> None:
    if not settings.stripe_api_key:
        raise RuntimeError("STRIPE_API_KEY is not set")
    stripe.api_key = settings.stripe_api_key


def create_checkout_session(
    user_id: str,
    user_email: str | None,
    tier: str,
    stripe_customer_id: str | None,
    base_url: str,
) -> dict:
    """Create a Stripe Checkout Session. Returns dict with 'url' key."""
    _ensure_api_key()

    if tier not in TIER_TO_PRICE_ID:
        raise ValueError(f"Unknown tier: {tier}")

    price_id = TIER_TO_PRICE_ID[tier]
    mode = "subscription" if tier in RECURRING_TIERS else "payment"

    params: dict = {
        "mode": mode,
        "success_url": f"{base_url}/account/billing?upgraded={tier}",
        "cancel_url": f"{base_url}/account/billing?cancelled=true",
        "metadata": {"user_id": user_id, "tier": tier},
        "line_items": [{"price": price_id, "quantity": 1}],
    }

    if stripe_customer_id:
        params["customer"] = stripe_customer_id
    else:
        params["customer_email"] = user_email

    session = stripe.checkout.Session.create(**params)
    return {"url": str(session.url or ""), "id": str(session.id)}


def create_billing_portal_session(
    stripe_customer_id: str,
    base_url: str,
) -> dict:
    """Create Stripe Customer Portal session. Returns dict with 'url' key."""
    _ensure_api_key()
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=f"{base_url}/account/billing",
    )
    return {"url": str(session.url)}


def verify_webhook_signature(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify Stripe webhook signature. Raises on invalid signature."""
    if not settings.stripe_webhook_secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not set")
    return stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
