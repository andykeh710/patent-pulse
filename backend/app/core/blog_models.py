"""Phase 6 PR 2 — Blog post model."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BlogPost(Base):
    """Editorial blog post with markdown content and structured relations."""

    __tablename__ = "blog_posts"

    slug: Mapped[str] = mapped_column(String(256), primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    subtitle: Mapped[str | None] = mapped_column(String(512), nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_markdown: Mapped[str] = mapped_column(Text)
    hero_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    author_name: Mapped[str] = mapped_column(String(128))
    author_role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    related_patent_doc_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    related_theme_slugs: Mapped[list[str]] = mapped_column(JSONB, default=list)
    related_company_names: Mapped[list[str]] = mapped_column(JSONB, default=list)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=text("now()"),
        onupdate=_utcnow,
    )
    status: Mapped[str] = mapped_column(
        String(16), default="draft", server_default="draft"
    )  # draft | published
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=text("now()")
    )
