"""Add onboarding fields to users table

Revision ID: 0028
Revises: 0027
Create Date: 2026-06-08

Adds three columns to track onboarding state:
- industry_focus: the industry/CPC area selected in wizard step 2
- interests_freetext: free-text example from wizard step 3
- onboarded_at: timestamp when wizard was completed (null = not onboarded)
"""

from alembic import op
import sqlalchemy as sa

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "industry_focus VARCHAR(64)"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "interests_freetext TEXT"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "onboarded_at TIMESTAMP"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS industry_focus")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS interests_freetext")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS onboarded_at")
