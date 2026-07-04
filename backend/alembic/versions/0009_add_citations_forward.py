"""add_citations_forward

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-23

Adds citations_forward column to patent_publications.
Mirrors the existing citations_backward pattern (JSONB, default []).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patent_publications",
        sa.Column(
            "citations_forward",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("patent_publications", "citations_forward")
