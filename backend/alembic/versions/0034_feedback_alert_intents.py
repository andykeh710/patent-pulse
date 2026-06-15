"""Create feedback and alert_intents tables for Sprint 7."""

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=True, index=True),
        sa.Column("route", sa.String(), nullable=False),
        sa.Column("surface", sa.String(), nullable=False),
        sa.Column("rating", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("object_type", sa.String(64), nullable=True),
        sa.Column("object_id", sa.String(64), nullable=True),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "alert_intents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False, index=True),
        sa.Column("alert_type", sa.String(), nullable=False),
        sa.Column("query_or_filter_json", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("frequency", sa.String(), nullable=False, server_default="weekly"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("alert_intents")
    op.drop_table("feedback")
