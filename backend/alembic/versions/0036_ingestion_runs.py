"""Ingestion run tracking table.

Stores metadata for each daily ingestion run so the freshness
endpoint and UI banner can distinguish "ingestion ran successfully
but found nothing new" from "ingestion hasn't run in days."
"""

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            comment="One of: started, success, failed",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grants_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("grants_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("grants_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("grants_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("apps_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("apps_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("apps_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("apps_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_runs_started_at", "ingestion_runs", ["started_at"])


def downgrade():
    op.drop_table("ingestion_runs")
