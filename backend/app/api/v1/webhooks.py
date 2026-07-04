"""
Resend webhook handler + public unsubscribe page.

POST /api/v1/webhooks/resend — receives Resend delivery events
GET  /unsubscribe/{token} — one-click unsubscribe, no auth
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, update

from app.config import settings
from app.core.ai_models import User
from app.core.subscription_models import EmailDelivery
from app.database import async_session_maker
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)
webhook_router = APIRouter(tags=["webhooks"])
public_router = APIRouter(tags=["public"])


# ── Resend webhook ───────────────────────────────────────────────


@webhook_router.post("/webhooks/resend")
@limiter.exempt
async def resend_webhook(request: Request) -> dict:
    """Handle Resend delivery events.

    Resend sends POST with JSON body containing:
    {type: "email.delivered"|"email.bounced"|"email.complained"|..., data: {...}}

    Maps bounce/complaint events to User preferences.
    """
    try:
        body = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid_json"}

    event_type = body.get("type", "")
    data = body.get("data", {})
    resend_id = data.get("email_id") or data.get("id", "")

    if event_type.startswith("email."):
        logger.info("Resend webhook: %s — %s", event_type, resend_id)

    # Update email_deliveries row if we can find it
    async with async_session_maker() as session:
        result = await session.execute(
            select(EmailDelivery).where(EmailDelivery.resend_message_id == str(resend_id))
        )
        delivery = result.scalar_one_or_none()
        if delivery:
            delivery.webhook_event = event_type
            delivery.webhook_received_at = datetime.now(timezone.utc)

            # Phase 5: record opens
            if event_type == "email.opened" and delivery.email_opened_at is None:
                delivery.email_opened_at = datetime.now(timezone.utc)
            # Phase 5: record clicks
            elif event_type == "email.clicked" and delivery.email_clicked_at is None:
                delivery.email_clicked_at = datetime.now(timezone.utc)
                delivery.click_url = (
                    data.get("click", {}).get("link") or data.get("url") or data.get("link", "")
                )
                delivery.click_url = (delivery.click_url or "")[:512]

            await session.commit()

    # Handle unsubscribe requests from Resend
    if event_type == "email.complained":
        await _handle_complaint(data)
    elif event_type == "email.bounced":
        await _handle_bounce(data)

    return {"status": "ok"}


async def _handle_complaint(data: dict) -> None:
    """Mark user as unsubscribed on complaint."""
    to_email = data.get("to") or data.get("email", "")
    if not to_email:
        return
    async with async_session_maker() as session:
        await session.execute(
            update(User)
            .where(User.email == to_email)
            .values(preferences=User.preferences.op("||")({"weekly_briefing_enabled": False}))
        )
        await session.commit()
        logger.info("Unsubscribed %s via Resend complaint webhook", to_email)


async def _handle_bounce(data: dict) -> None:
    """Log bounce but don't auto-unsubscribe (single bounce could be temporary)."""
    to_email = data.get("to") or data.get("email", "")
    logger.warning("Bounce received for %s", to_email)


# ── Public unsubscribe page ──────────────────────────────────────


@public_router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe_page(token: str):
    """One-click unsubscribe. No auth required. JWT token identifies the user."""
    import jwt

    try:
        payload = jwt.decode(
            token,
            settings.auth_secret_key or "dev-secret-change-me",
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        return _unsubscribe_html("expired")
    except Exception:
        return _unsubscribe_html("invalid")

    user_id = payload.get("user_id")
    purpose = payload.get("purpose")
    if not user_id or purpose != "unsubscribe":
        return _unsubscribe_html("invalid")

    # Update user
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return _unsubscribe_html("not_found")

        current_prefs = user.preferences or {}
        current_prefs["weekly_briefing_enabled"] = False
        user.preferences = current_prefs
        await session.commit()

    logger.info("User %s unsubscribed via token", user_id)
    return _unsubscribe_html("success")


@public_router.post("/api/v1/account/unsubscribe")
async def unsubscribe_by_token(payload: dict) -> dict:
    """API endpoint for unsubscribe token verification (used by email clients)."""
    return await _verify_unsubscribe(payload.get("token", ""))


async def _verify_unsubscribe(token: str) -> dict:
    import jwt

    try:
        payload = jwt.decode(
            token, settings.auth_secret_key or "dev-secret-change-me", algorithms=["HS256"]
        )
        user_id = payload.get("user_id")
        if not user_id:
            return {"status": "invalid"}
        async with async_session_maker() as session:
            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(preferences=User.preferences.op("||")({"weekly_briefing_enabled": False}))
            )
            await session.commit()
        return {"status": "unsubscribed"}
    except Exception:
        return {"status": "invalid"}


def _unsubscribe_html(state: str) -> str:
    messages = {
        "success": ("Unsubscribed", "You have been unsubscribed from weekly briefings.", "#22C55E"),
        "expired": (
            "Link Expired",
            "This unsubscribe link has expired. Visit your account settings to manage email preferences.",
            "#F59E0B",
        ),
        "invalid": ("Invalid Link", "This unsubscribe link is not valid.", "#EF4444"),
        "not_found": (
            "Account Not Found",
            "We couldn't find an account matching this link.",
            "#EF4444",
        ),
    }
    title, message, color = messages.get(state, messages["invalid"])
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body style="font-family:Helvetica,Arial,sans-serif;max-width:480px;margin:60px auto;padding:24px;background:#0B0E14;color:#E5E7EB;text-align:center;">
<h1 style="color:{color};font-size:20px;">{title}</h1>
<p style="font-size:14px;color:#9CA3AF;">{message}</p>
<a href="{settings.magic_link_base_url}" style="display:inline-block;margin-top:16px;padding:10px 20px;background:#1E2433;color:#6B8CFF;border-radius:6px;text-decoration:none;">Back to Invention Index 8</a>
</body></html>"""
