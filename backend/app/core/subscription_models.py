"""Sprint 6 — Subscription, auth, and email delivery ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

# Import User model to ensure it's registered in Base.metadata before
# we reference it via ForeignKey("users.id") below.
from app.core.ai_models import User as _User  # noqa: F401
from app.core.models import Base


def _utcnow():
    return datetime.now(timezone.utc)


class TopicSubscription(Base):
    """User subscription to a theme for alerts or weekly digests."""

    __tablename__ = "topic_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"))
    theme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("themes.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(String(16))
    min_score: Mapped[float | None] = mapped_column(Float)
    last_delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "theme_id", "mode", name="uq_topic_subscriptions_user_theme_mode"
        ),
        Index("ix_topic_subscriptions_user_id", "user_id"),
        Index("ix_topic_subscriptions_theme_id", "theme_id"),
    )


class AuthMagicLinkToken(Base):
    """Single-use magic-link authentication token (hashed)."""

    __tablename__ = "auth_magic_link_tokens"

    token_hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(256))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=text("now()")
    )

    __table_args__ = (Index("ix_auth_magic_link_tokens_user_id", "user_id"),)


class EmailDelivery(Base):
    """Record of each email sent — audit trail."""

    __tablename__ = "email_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("topic_subscriptions.id", ondelete="SET NULL")
    )
    email_type: Mapped[str] = mapped_column(String(32))
    resend_message_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=text("now()")
    )
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_artifacts.id"))
    # Resend webhook fields
    webhook_event: Mapped[str | None] = mapped_column(String(32), nullable=True)
    webhook_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Phase 5: A/B subject line variant
    subject_variant: Mapped[str | None] = mapped_column(String(1), nullable=True)

    # Phase 5: Open + click tracking via Resend webhook
    email_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_clicked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    click_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    __table_args__ = (
        Index("ix_email_deliveries_user_id", "user_id"),
        Index("ix_email_deliveries_subscription_id", "subscription_id"),
        Index("ix_email_deliveries_subject_variant", "subject_variant"),
        Index("ix_email_deliveries_webhook_event", "webhook_event"),
    )
