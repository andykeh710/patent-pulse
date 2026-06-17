"""fix_user_auth_defaults

Revision ID: 0029
Revises: 0028
Create Date: 2026-06-17

"""
import os

import sqlalchemy as sa

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    default_user_id = os.getenv("DEFAULT_USER_ID", "local-user")
    op.alter_column(
        "users",
        "display_name",
        existing_type=sa.String(length=128),
        existing_nullable=False,
        nullable=True,
    )
    op.execute(
        sa.text("UPDATE users SET is_admin = false WHERE id <> :default_user_id")
        .bindparams(default_user_id=default_user_id)
    )
    op.alter_column(
        "users",
        "is_admin",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        server_default=sa.text("false"),
    )


def downgrade() -> None:
    op.execute("UPDATE users SET display_name = COALESCE(email, id) WHERE display_name IS NULL")
    op.alter_column(
        "users",
        "display_name",
        existing_type=sa.String(length=128),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "users",
        "is_admin",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        server_default=sa.text("true"),
    )
