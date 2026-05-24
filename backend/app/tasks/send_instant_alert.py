"""
Instant alert delivery task (Sprint 6).

Triggered by theme_matcher when a new patent matches a subscribed theme.
Idempotent within a 1-hour window per (subscription, patent).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, text

from app.config import settings
from app.core.models import PatentPublication
from app.core.theme_models import Theme
from app.core.subscription_models import TopicSubscription, EmailDelivery
from app.database import async_session_maker
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.send_instant_alert.send_instant_alert",
    max_retries=2,
    default_retry_delay=60,
)
def send_instant_alert(self, subscription_id: str, patent_id: str, match_id: str) -> dict:
    """Send an instant alert email for a new theme match.

    Args:
        subscription_id: topic_subscriptions.id (UUID string)
        patent_id: patent_publications.id (UUID string)
        match_id: theme_matches.id (UUID string) — for logging, not dedup.

    Returns: status dict.
    """
    logger.info(
        "Dispatching instant alert: sub=%s patent=%s match=%s",
        subscription_id, patent_id, match_id,
    )

    from app.database import engine as _engine

    async def _run_and_dispose():
        try:
            return await _send_instant_alert_async(subscription_id, patent_id, match_id)
        finally:
            await _engine.dispose()

    try:
        stats = asyncio.run(_run_and_dispose())
    except Exception as e:
        logger.error("Instant alert failed: %s", e)
        stats = {"status": "failed", "error": str(e)}

    return stats


async def _send_instant_alert_async(subscription_id: str, patent_id: str, match_id: str) -> dict:
    sub_uuid = UUID(subscription_id)
    patent_uuid = UUID(patent_id)

    async with async_session_maker() as session:
        try:
            # ── fetch rows ──
            sub = (await session.execute(
                select(TopicSubscription).where(TopicSubscription.id == sub_uuid)
            )).scalar_one_or_none()
            if not sub:
                return {"status": "skipped", "reason": "subscription not found"}

            patent = (await session.execute(
                select(PatentPublication).where(PatentPublication.id == patent_uuid)
            )).scalar_one_or_none()
            if not patent:
                return {"status": "skipped", "reason": "patent not found"}

            theme = (await session.execute(
                select(Theme).where(Theme.id == sub.theme_id)
            )).scalar_one_or_none()
            if not theme:
                return {"status": "skipped", "reason": "theme not found"}

            # ── min_score filter ──
            if sub.min_score is not None:
                opp_score = getattr(patent, "opportunity_score", None) or 0
                if opp_score < sub.min_score:
                    return {"status": "skipped", "reason": "below min_score"}

            # ── idempotency: check last delivery within 1 hour ──
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            recent = (await session.execute(
                select(EmailDelivery).where(
                    EmailDelivery.subscription_id == sub_uuid,
                    EmailDelivery.email_type == "instant_alert",
                    EmailDelivery.sent_at >= one_hour_ago,
                )
            )).scalar_one_or_none()
            if recent:
                return {"status": "skipped", "reason": "delivered within last hour"}

            # ── build template data ──
            summary = (
                getattr(patent, "summary", None)
                or ((patent.abstract or "")[:200])
                or "No summary available"
            )
            unsubscribe_token = _sign_subscription_id(sub_uuid)
            unsubscribe_url = (
                f"{settings.magic_link_base_url}"
                f"/api/v1/subscriptions/unsubscribe"
                f"?subscription={sub_uuid}&token={unsubscribe_token}"
            )

            # ── lookup user email ──
            from app.core.ai_models import User
            user_row = (await session.execute(
                select(User).where(User.id == sub.user_id)
            )).scalar_one_or_none()
            user_email = user_row.email or "unknown@example.com" if user_row else "unknown@example.com"

            from app.email.sender import send_email
            result = await send_email(
                db_session=session,
                to=user_email,
                subject=f"New match: {patent.title or patent.doc_id}",
                template_name="instant_alert.html",
                template_kwargs={
                    "topic_name": theme.name,
                    "match_count": "1",
                    "patents": [{
                        "title": patent.title or patent.doc_id,
                        "url": f"{settings.magic_link_base_url}/patents/{patent.id}",
                        "assignee": (patent.assignees or [""])[0],
                        "publication_number": patent.publication_number or "",
                        "expiry_status": getattr(patent, "legal_status", "unknown"),
                        "abstract_snippet": summary,
                    }],
                    "unsubscribe_url": unsubscribe_url,
                    "magic_link_base_url": settings.magic_link_base_url,
                },
                user_id=sub.user_id,
                email_type="instant_alert",
                subscription_id=sub_uuid,
            )

            # ── update last_delivered_at ──
            if result.get("status") in ("sent", "dev", "dry_run"):
                sub.last_delivered_at = datetime.now(timezone.utc)
                await session.commit()

            return result

        except Exception as e:
            logger.error("Error in _send_instant_alert_async: %s", e)
            return {"status": "failed", "error": str(e)}


def _sign_subscription_id(subscription_id: UUID) -> str:
    import hashlib, hmac
    return hmac.new(
        settings.auth_secret_key.encode(),
        str(subscription_id).encode(),
        hashlib.sha256,
    ).hexdigest()
