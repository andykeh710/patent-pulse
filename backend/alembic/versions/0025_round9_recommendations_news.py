"""round 9: user_view_events, user_embeddings, news_items, news_patent_links

Revision ID: 0025
Revises: 0024
Create Date: 2026-06-04

Creates the four tables required by the Round 9 recommendation and news
ingestion features. Without this migration the /for-you endpoint and the
ingest_news Celery task will fail at runtime.
"""
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_view_events",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(64), nullable=False, index=True),
        sa.Column(
            "patent_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patent_publications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("weight", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_user_view_events_user",
        "user_view_events",
        ["user_id", "created_at"],
    )

    op.create_table(
        "user_embeddings",
        sa.Column("user_id", sa.String(64), primary_key=True),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("event_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "news_items",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("headline", sa.String(512), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("snippet", sa.Text, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_news_items_published", "news_items", ["published_at"])

    op.create_table(
        "news_patent_links",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "news_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("news_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "patent_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patent_publications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("similarity", sa.Float, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_news_patent_links_news", "news_patent_links", ["news_id"])


def downgrade() -> None:
    op.drop_index("ix_news_patent_links_news", table_name="news_patent_links")
    op.drop_table("news_patent_links")
    op.drop_index("ix_news_items_published", table_name="news_items")
    op.drop_table("news_items")
    op.drop_table("user_embeddings")
    op.drop_index("ix_user_view_events_user", table_name="user_view_events")
    op.drop_table("user_view_events")
