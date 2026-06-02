"""user_persona_column

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-01

"""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("persona", sa.String(16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "persona")
