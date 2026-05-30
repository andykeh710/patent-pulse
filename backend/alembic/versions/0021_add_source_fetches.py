"""Add source_fetches table.

Revision ID: 0021
Revises: 0020
Create Date: 2026-05-29

Tracks every external data fetch: provider, target, status, timing, error info.
Used by data-health dashboard and ingestion diagnostics.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_fetches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider", sa.String(64), nullable=False, index=True),
        sa.Column("office", sa.String(16), nullable=True, index=True),
        sa.Column("target_type", sa.String(32), nullable=False, index=True),
        sa.Column("target_id", sa.String(128), nullable=True, index=True),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, index=True, server_default="pending"),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("records_found", sa.Integer(), nullable=True),
        sa.Column("raw_storage_key", sa.String(512), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("source_fetches")
