"""
Resend email sender with send-mode guard (Sprint 6).

Modes: dev | dry_run | production (gated behind EMAIL_PRODUCTION_ACKNOWLEDGED).
Every send writes an EmailDelivery row for the audit trail.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.subscription_models import EmailDelivery

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    undefined=StrictUndefined,
)


def _render(template_name: str, **kwargs: object) -> str:
    """Render a Jinja2 template with strict variable checking."""
    template = _jinja_env.get_template(template_name)
    return template.render(**kwargs)


async def send_email(
    *,
    db_session: AsyncSession,
    to: str,
    subject: str,
    template_name: str,
    template_kwargs: dict[str, object] | None = None,
    user_id: str,
    email_type: str,
    subscription_id: UUID | None = None,
    artifact_id: UUID | None = None,
    subject_variant: str | None = None,
) -> dict[str, str]:
    """Send an email via Resend with mode-guard. Writes EmailDelivery row.

    Returns {"status": "sent"|"dev"|"dry_run"|"refused"|"failed", "detail": ...}.
    """
    mode = settings.email_send_mode or "dev"
    kwargs = template_kwargs or {}
    resend_id: str | None = None

    # ── production gate ──
    if mode == "production":
        acknowledged = os.getenv("EMAIL_PRODUCTION_ACKNOWLEDGED", "").lower()
        if acknowledged != "true":
            logger.error(
                "EMAIL_SEND_MODE=production but EMAIL_PRODUCTION_ACKNOWLEDGED "
                "is not 'true'. Refusing to send to %s.",
                to,
            )
            await _write_delivery(
                db_session,
                user_id,
                email_type,
                subscription_id,
                artifact_id,
                status="refused",
                detail="Production not acknowledged",
                subject_variant=subject_variant,
            )
            return {"status": "refused", "detail": "Production not acknowledged"}

    # ── render template ──
    try:
        html = _render(template_name, **kwargs)
    except Exception as e:
        logger.error("Template error (%s): %s", template_name, e)
        await _write_delivery(
            db_session,
            user_id,
            email_type,
            subscription_id,
            artifact_id,
            status="failed",
            detail=str(e),
            subject_variant=subject_variant,
        )
        return {"status": "failed", "detail": str(e)}

    # ── dev mode ──
    if mode == "dev":
        dev_to = settings.email_dev_recipient or to
        subject = f"[DEV → {to}] {subject}"
        logger.info("DEV MODE: redirecting to %s", dev_to)
        _log_preview(subject, dev_to, html)

        if settings.resend_api_key:
            try:
                import resend

                resend.api_key = settings.resend_api_key
                r = resend.Emails.send(
                    {
                        "from": settings.email_from_address,
                        "to": [dev_to],
                        "subject": subject,
                        "html": html,
                    }
                )
                resend_id = str(r.get("id", "dev"))
            except Exception as e:
                logger.error("Resend API error (dev): %s", e)

        await _write_delivery(
            db_session,
            user_id,
            email_type,
            subscription_id,
            artifact_id,
            status="dev",
            detail="Redirected to dev recipient",
            resend_id=resend_id,
            subject_variant=subject_variant,
        )
        return {"status": "dev", "detail": resend_id or "Logged"}

    # ── dry_run mode ──
    if mode == "dry_run":
        _log_preview(subject, to, html)
        await _write_delivery(
            db_session,
            user_id,
            email_type,
            subscription_id,
            artifact_id,
            status="dry_run",
            detail="Template rendered",
            subject_variant=subject_variant,
        )
        return {"status": "dry_run", "detail": "Template rendered"}

    # ── production ──
    if mode == "production" and settings.resend_api_key:
        try:
            import resend

            resend.api_key = settings.resend_api_key
            r = resend.Emails.send(
                {
                    "from": settings.email_from_address,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                }
            )
            resend_id = str(r.get("id", "sent"))
        except Exception as e:
            logger.error("Resend API error (production): %s", e)
            await _write_delivery(
                db_session,
                user_id,
                email_type,
                subscription_id,
                artifact_id,
                status="failed",
                detail=str(e),
                subject_variant=subject_variant,
            )
            return {"status": "failed", "detail": str(e)}

        await _write_delivery(
            db_session,
            user_id,
            email_type,
            subscription_id,
            artifact_id,
            status="sent",
            detail="",
            resend_id=resend_id,
            subject_variant=subject_variant,
        )
        return {"status": "sent", "detail": resend_id}

    logger.error("No Resend API key configured or unknown mode '%s'", mode)
    await _write_delivery(
        db_session,
        user_id,
        email_type,
        subscription_id,
        artifact_id,
        status="failed",
        detail="No API key or unknown mode",
        subject_variant=subject_variant,
    )
    return {"status": "failed", "detail": "No API key or unknown mode"}


async def _write_delivery(
    db_session: AsyncSession,
    user_id: str,
    email_type: str,
    subscription_id: UUID | None,
    artifact_id: UUID | None,
    *,
    status: str,
    detail: str,
    resend_id: str | None = None,
    subject_variant: str | None = None,
) -> None:
    """Write an email_deliveries row (audit trail)."""
    try:
        row = EmailDelivery(
            user_id=user_id,
            subscription_id=subscription_id,
            email_type=email_type,
            resend_message_id=resend_id,
            status=status,
            artifact_id=artifact_id,
            subject_variant=subject_variant,
        )
        db_session.add(row)
        await db_session.commit()
    except Exception as e:
        logger.error("Failed to write email delivery row: %s", e)


def _log_preview(subject: str, to: str, html: str) -> None:
    preview = html[:500].replace("\n", " ")
    logger.info("Email preview [%s → %s]: %s", subject, to, preview)
