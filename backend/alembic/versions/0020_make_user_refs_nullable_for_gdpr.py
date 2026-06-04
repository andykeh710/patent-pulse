"""make user refs nullable for GDPR account deletion

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-28

Makes email_deliveries.user_id and ai_runs.created_by nullable so
that when a user deletes their account (GDPR right to erasure), those
columns can be set to NULL instead of requiring the rows to be
deleted.  The FK on-delete action is changed to SET NULL to support
this: deleting a users row will automatically NULL out referencing
email_deliveries and ai_runs rows, preserving the audit trail.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_fk_and_make_nullable(
    table: str,
    column: str,
    fk_name: str,
    ref_table: str = "users",
    ref_column: str = "id",
) -> None:
    """Drop FK, make column nullable, re-add FK with ON DELETE SET NULL."""
    op.drop_constraint(fk_name, table, type_="foreignkey")
    op.alter_column(table, column, nullable=True)
    op.create_foreign_key(
        fk_name, table, ref_table, [column], [ref_column], ondelete="SET NULL"
    )


def upgrade() -> None:
    _drop_fk_and_make_nullable(
        "email_deliveries", "user_id", "email_deliveries_user_id_fkey"
    )
    _drop_fk_and_make_nullable(
        "ai_runs", "created_by", "ai_runs_created_by_fkey"
    )


def downgrade() -> None:
    # email_deliveries
    op.drop_constraint(
        "email_deliveries_user_id_fkey", "email_deliveries", type_="foreignkey"
    )
    op.alter_column("email_deliveries", "user_id", nullable=False)
    op.create_foreign_key(
        "email_deliveries_user_id_fkey",
        "email_deliveries", "users",
        ["user_id"], ["id"],
    )

    # ai_runs
    op.drop_constraint(
        "ai_runs_created_by_fkey", "ai_runs", type_="foreignkey"
    )
    op.alter_column("ai_runs", "created_by", nullable=False)
    op.create_foreign_key(
        "ai_runs_created_by_fkey",
        "ai_runs", "users",
        ["created_by"], ["id"],
    )
