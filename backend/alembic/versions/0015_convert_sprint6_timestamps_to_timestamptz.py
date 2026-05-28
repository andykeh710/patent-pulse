"""convert_sprint6_timestamps_to_timestamptz

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-25

Convert 7 TIMESTAMP columns across Sprint 6 tables to TIMESTAMPTZ
for consistent timezone-aware datetime handling.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TZ_COLUMNS = {
    "auth_magic_link_tokens": ["expires_at", "consumed_at", "created_at"],
    "topic_subscriptions": ["last_delivered_at", "created_at", "updated_at"],
    "email_deliveries": ["sent_at"],
}


def upgrade() -> None:
    for table, columns in TZ_COLUMNS.items():
        for col in columns:
            op.alter_column(
                table,
                col,
                type_=sa.DateTime(timezone=True),
                postgresql_using=f"{col} AT TIME ZONE 'UTC'",
            )


def downgrade() -> None:
    for table, columns in TZ_COLUMNS.items():
        for col in columns:
            op.alter_column(
                table,
                col,
                type_=sa.DateTime(),
                postgresql_using=f"{col} AT TIME ZONE 'UTC'",
            )
