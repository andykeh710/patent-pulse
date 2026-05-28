"""add_figure_page_url

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-23

Adds figure_page_url column to patent_publications — stores a LINK-OUT
URL to Google Patents thumbnails page. Not an inline image URL.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patent_publications",
        sa.Column("figure_page_url", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("patent_publications", "figure_page_url")
