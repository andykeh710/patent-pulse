"""Add abstract_source and claims_source provenance columns.

Revision ID: 0022
Revises: 0021
Create Date: 2026-05-30
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patent_publications", sa.Column("abstract_source", sa.String(32), nullable=True))
    op.add_column("patent_publications", sa.Column("claims_source", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("patent_publications", "claims_source")
    op.drop_column("patent_publications", "abstract_source")
