"""Sprint 6 — Subscription, auth, and email delivery ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base

# Import User model to ensure it's registered in Base.metadata before
# we reference it via ForeignKey("users.id") below.
from app.core.ai_models import User as _User  # noqa: F401


class TopicSubscription(Base):
    """User subscription to a theme for alerts or weekly digests."""

    __tablename__ = "topic_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE")
    )
    theme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("themes.id", ondelete="CASCADE")
    )
    mode: Mapped[str] = mapped_column(String(16))  # 'instant_alert' | 'weekly_digest'
    min_score: Mapped[float | None] = mapped_column(Float)
    last_delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "theme_id", "mode", name="uq_topic_subscriptions_user_theme_mode"),
        Index("ix_topic_subscriptions_user_id", "user_id"),
        Index("ix_topic_subscriptions_theme_id", "theme_id"),
    )


class AuthMagicLinkToken(Base):
    """Single-use magic-link authentication token (hashed)."""

    __tablename__ = "auth_magic_link_tokens"

    token_hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE")
    )
    email: Mapped[str] = mapped_column(String(256))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )

    __table_args__ = (
        Index("ix_auth_magic_link_tokens_user_id", "user_id"),
    )


class EmailDelivery(Base):
    """Record of each email sent — audit trail."""

    __tablename__ = "email_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"))
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("topic_subscriptions.id", ondelete="SET NULL")
    )
    email_type: Mapped[str] = mapped_column(String(32))
    resend_message_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_artifacts.id")
    )

    __table_args__ = (
        Index("ix_email_deliveries_user_id", "user_id"),
        Index("ix_email_deliveries_subscription_id", "subscription_id"),
    )
