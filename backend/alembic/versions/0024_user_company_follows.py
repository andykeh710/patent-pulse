"""user_company_follows

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-01

"""
import sqlalchemy as sa

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_company_follows",
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_normalized_name", sa.Text, nullable=False),
        sa.Column("display_name", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "company_normalized_name"),
    )
    op.create_index(
        "ix_user_company_follows_user_id",
        "user_company_follows",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_company_follows_user_id", table_name="user_company_follows")
    op.drop_table("user_company_follows")
