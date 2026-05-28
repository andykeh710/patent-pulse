"""add_email_deliveries

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_deliveries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.String(64),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("topic_subscriptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("email_type", sa.String(32), nullable=False),
        sa.Column("resend_message_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_artifacts.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_email_deliveries_user_id",
        "email_deliveries",
        ["user_id"],
    )
    op.create_index(
        "ix_email_deliveries_subscription_id",
        "email_deliveries",
        ["subscription_id"],
    )


def downgrade() -> None:
    op.drop_table("email_deliveries")
