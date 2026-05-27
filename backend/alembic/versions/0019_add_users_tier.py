"""add_users_tier

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "tier",
            sa.String(16),
            nullable=False,
            server_default="free",
        ),
    )
    op.create_index("ix_users_tier", "users", ["tier"])


def downgrade() -> None:
    op.drop_index("ix_users_tier", table_name="users")
    op.drop_column("users", "tier")
