"""Phase 5 PR 1 — email_deliveries: webhook + subject_variant + open/click tracking

Revision ID: 0029
Revises: 0028_user_onboarding_fields
Create Date: 2026-06-08
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Resend webhook fields (referenced by existing code in webhooks.py)
    op.add_column(
        "email_deliveries",
        sa.Column("webhook_event", sa.String(32), nullable=True),
    )
    op.add_column(
        "email_deliveries",
        sa.Column("webhook_received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_email_deliveries_webhook_event",
        "email_deliveries",
        ["webhook_event"],
    )

    # Phase 5: A/B subject line variant
    op.add_column(
        "email_deliveries",
        sa.Column("subject_variant", sa.String(1), nullable=True),
    )
    op.create_index(
        "ix_email_deliveries_subject_variant",
        "email_deliveries",
        ["subject_variant"],
    )

    # Phase 5: Open + click tracking
    op.add_column(
        "email_deliveries",
        sa.Column("email_opened_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "email_deliveries",
        sa.Column("email_clicked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "email_deliveries",
        sa.Column("click_url", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_index("ix_email_deliveries_webhook_event", table_name="email_deliveries")
    op.drop_column("email_deliveries", "webhook_received_at")
    op.drop_column("email_deliveries", "webhook_event")

    op.drop_index("ix_email_deliveries_subject_variant", table_name="email_deliveries")
    op.drop_column("email_deliveries", "subject_variant")

    op.drop_column("email_deliveries", "click_url")
    op.drop_column("email_deliveries", "email_clicked_at")
    op.drop_column("email_deliveries", "email_opened_at")
