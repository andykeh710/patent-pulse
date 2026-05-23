"""add_expiry_assessments

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-22

Adds expiry_assessments table for deterministic expiry status, confidence,
active family risk, and legal caveats. This is a derived layer on top of
PatentPublication expiry fields — does not replace them.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expiry_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "patent_publication_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patent_publications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("estimated_expiry_date", sa.Date(), nullable=True),
        sa.Column(
            "expiry_status",
            sa.String(32),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column(
            "expiry_status_confidence",
            sa.String(16),
            nullable=False,
            server_default="low",
        ),
        sa.Column("maintenance_status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("maintenance_status_source", sa.String(64), nullable=True),
        sa.Column("active_family_risk", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("active_family_risk_reason", sa.Text(), nullable=True),
        sa.Column("terminal_disclaimer_flag", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("patent_term_adjustment_days", sa.Integer(), nullable=True),
        sa.Column("legal_caveats", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("assessment_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "source_updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_expiry_assessments_patent_id",
        "expiry_assessments",
        ["patent_publication_id"],
    )
    op.create_index(
        "ix_expiry_assessments_status",
        "expiry_assessments",
        ["expiry_status"],
    )
    op.create_index(
        "ix_expiry_assessments_confidence",
        "expiry_assessments",
        ["expiry_status_confidence"],
    )
    op.create_index(
        "ix_expiry_assessments_expiry_date",
        "expiry_assessments",
        ["estimated_expiry_date"],
    )
    op.create_index(
        "ix_expiry_assessments_family_risk",
        "expiry_assessments",
        ["active_family_risk"],
    )


def downgrade() -> None:
    op.drop_table("expiry_assessments")
