"""Add last_today_seen_at + previous_today_seen_at to users table.

Sprint 3 — Since-last-visit tracking for the Today habit engine.
Both columns are nullable DateTime(timezone=True).  The mark-seen
endpoint shifts last_seen → previous_seen on each Today view so
the frontend can show a comparison window.

No backfill needed — columns default to NULL. First-time users
see "Welcome — your first Today briefing".
"""

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column("users", sa.Column("last_today_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("previous_today_seen_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "previous_today_seen_at")
    op.drop_column("users", "last_today_seen_at")
