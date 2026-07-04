"""Phase 6 PR 2 — blog_posts table

Revision ID: 0031
Revises: 0030_alerts_webhook_configs
Create Date: 2026-06-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0031"
down_revision: Union[str, None] = "0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "blog_posts",
        sa.Column("slug", sa.String(256), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("subtitle", sa.String(512), nullable=True),
        sa.Column("excerpt", sa.Text, nullable=True),
        sa.Column("content_markdown", sa.Text, nullable=False),
        sa.Column("hero_image_url", sa.String(1024), nullable=True),
        sa.Column("author_name", sa.String(128), nullable=False),
        sa.Column("author_role", sa.String(128), nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "related_patent_doc_ids", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "related_theme_slugs", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "related_company_names", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("blog_posts")
