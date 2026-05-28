"""add_content_drafts

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-22

Adds content_drafts table for user-facing generated content (LinkedIn posts, etc.).
user_id is a plain string (no FK) matching the watchlist_items convention.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False, server_default="anonymous"),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("prompt_hash", sa.String(64), nullable=True),
        sa.Column(
            "artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_artifacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_content_drafts_user_id", "content_drafts", ["user_id"])
    op.create_index("ix_content_drafts_source_type", "content_drafts", ["source_type"])
    op.create_index("ix_content_drafts_source_id", "content_drafts", ["source_id"])
    op.create_index("ix_content_drafts_content_type", "content_drafts", ["content_type"])


def downgrade() -> None:
    op.drop_table("content_drafts")
