"""
Theme and Watchlist Models.

Themes: Tracked technology areas defined by CPC prefixes and keywords.
Watchlists: User-saved patents for tracking.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import Base


class Theme(Base):
    """
    A tracked technology theme.

    Themes group patents by CPC prefixes, assignee keywords, or other criteria.
    Used for theme pages and alerts.
    """

    __tablename__ = "themes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    cpc_prefixes: Mapped[list[str]] = mapped_column(JSON, default=list)
    assignee_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    title_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Topic fields (for user-created topics; NULL for system themes)
    keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    opportunity_tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    min_opportunity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, default=None)

    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    matches: Mapped[list["ThemeMatch"]] = relationship(back_populates="theme")

    def __repr__(self) -> str:
        return f"<Theme {self.name}>"


class ThemeMatch(Base):
    """
    A patent matched to a theme.

    Records which patents belong to which themes and their match score.
    """

    __tablename__ = "theme_matches"
    __table_args__ = (UniqueConstraint("theme_id", "patent_id", name="ix_theme_matches_unique"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    theme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("themes.id"), index=True)
    patent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patent_publications.id"), index=True)

    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    match_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)

    matched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    theme: Mapped[Theme] = relationship(back_populates="matches")


class WatchlistItem(Base):
    """
    A patent saved to a user's watchlist.

    Note: user_id is a placeholder until Phase 4 auth is implemented.
    """

    __tablename__ = "watchlist_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="anonymous")
    patent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patent_publications.id"), index=True)

    note: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
