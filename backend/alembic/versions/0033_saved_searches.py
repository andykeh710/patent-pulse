"""Create saved_searches table for Sprint 4.5."""

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "saved_searches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("query", sa.String(), nullable=False, server_default=""),
        sa.Column("mode", sa.String(), nullable=False, server_default="hybrid"),
        sa.Column("filters_json", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("sort_by", sa.String(), nullable=False, server_default="relevance"),
        sa.Column("sort_order", sa.String(), nullable=False, server_default="desc"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("saved_searches")
