"""Add presentation_rank fields to patent_publications.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-29

Adds:
 - Columns on ``patent_publications``: presentation_rank_score,
   presentation_rank_reason, presentation_rank_confidence,
   presentation_rank_artifact_id.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patent_publications",
        sa.Column("presentation_rank_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "patent_publications",
        sa.Column("presentation_rank_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "patent_publications",
        sa.Column(
            "presentation_rank_confidence",
            sa.String(16),
            nullable=True,
        ),
    )
    op.add_column(
        "patent_publications",
        sa.Column(
            "presentation_rank_artifact_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_patent_publications_presentation_rank_score",
        "patent_publications",
        ["presentation_rank_score"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_patent_publications_presentation_rank_score",
        table_name="patent_publications",
    )
    op.drop_column("patent_publications", "presentation_rank_artifact_id")
    op.drop_column("patent_publications", "presentation_rank_confidence")
    op.drop_column("patent_publications", "presentation_rank_reason")
    op.drop_column("patent_publications", "presentation_rank_score")
