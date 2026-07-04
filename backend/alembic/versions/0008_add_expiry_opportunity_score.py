"""add_expiry_opportunity_score

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-22

Adds expiry_opportunity_score and expiry_opportunity_breakdown columns
to expiry_assessments. These are deterministic (not LLM-produced) scores
that assess how valuable an expired/expiring patent is for opportunity
discovery.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "expiry_assessments",
        sa.Column("expiry_opportunity_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "expiry_assessments",
        sa.Column(
            "expiry_opportunity_breakdown",
            postgresql.JSONB(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("expiry_assessments", "expiry_opportunity_breakdown")
    op.drop_column("expiry_assessments", "expiry_opportunity_score")
