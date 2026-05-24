"""add_topic_subscriptions

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "topic_subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "theme_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("themes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("min_score", sa.Float, nullable=True),
        sa.Column("last_delivered_at", sa.DateTime, nullable=True),
        sa.Column(
            "paused", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_unique_constraint(
        "uq_topic_subscriptions_user_theme_mode",
        "topic_subscriptions",
        ["user_id", "theme_id", "mode"],
    )
    op.create_index(
        "ix_topic_subscriptions_user_id",
        "topic_subscriptions",
        ["user_id"],
    )
    op.create_index(
        "ix_topic_subscriptions_theme_id",
        "topic_subscriptions",
        ["theme_id"],
    )


def downgrade() -> None:
    op.drop_table("topic_subscriptions")
