"""add_auth_magic_link_tokens

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-24

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_magic_link_tokens",
        sa.Column("token_hash", sa.String(128), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(256), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("consumed_at", sa.DateTime, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_auth_magic_link_tokens_user_id",
        "auth_magic_link_tokens",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_table("auth_magic_link_tokens")
