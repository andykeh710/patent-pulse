"""assignee table indexes and normalize_assignee function

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-08

Creates the normalize_assignee() PostgreSQL function (if it doesn't
already exist) and two expression indexes on the assignees table.
The function and indexes were applied directly to production during
a Phase 0 investigation session; this migration codifies them for
fresh environments and CI.

Without these indexes the OR-based join condition in the suppliers
API queries causes sequential scans of the full assignees table per
unrolled assignee row, saturating the DB on moderate traffic.
"""

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None

NORMALIZE_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION normalize_assignee(name text) RETURNS text AS $$
DECLARE
    result text;
BEGIN
    result := upper(trim(name));
    -- Remove content in brackets [KR], [US], etc.
    result := regexp_replace(result, '\\s*\\[[^\\]]+\\]\\s*$', '', 'g');
    -- Remove all periods (simplifies suffix matching)
    result := replace(result, '.', '');
    -- Remove trailing commas
    result := regexp_replace(result, '[,]+$', '', 'g');
    -- Normalize common suffixes (order matters — longer first)
    result := regexp_replace(result, '\\s+INCORPORATED\\s*$', ' INC', 'g');
    result := regexp_replace(result, '\\s+CORPORATION\\s*$', ' CORP', 'g');
    result := regexp_replace(result, '\\s+LIMITED\\s+LIABILITY\\s+COMPANY\\s*$', ' LLC', 'g');
    result := regexp_replace(result, '\\s+LIMITED\\s*$', ' LTD', 'g');
    result := regexp_replace(result, '\\s+LTD\\s*$', ' LTD', 'g');
    result := regexp_replace(result, '\\s+INC\\s*$', ' INC', 'g');
    result := regexp_replace(result, '\\s+CORP\\s*$', ' CORP', 'g');
    result := regexp_replace(result, '\\s+COMPANY\\s*$', ' CO', 'g');
    result := regexp_replace(result, '\\s+CO\\s*$', ' CO', 'g');
    result := regexp_replace(result, '\\s+LLC\\s*$', ' LLC', 'g');
    result := regexp_replace(result, '\\s+GMBH\\s*$', ' GMBH', 'g');
    result := regexp_replace(result, '\\s+SA\\s*$', ' SA', 'g');
    -- Remove remaining commas
    result := replace(result, ',', '');
    -- Normalize multiple spaces
    result := regexp_replace(result, '\\s+', ' ', 'g');
    result := trim(result);
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""


def upgrade() -> None:
    op.execute(NORMALIZE_FUNCTION_SQL)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_assignees_display_name_lower "
        "ON assignees (lower(display_name))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_assignees_normalized_name_lower "
        "ON assignees (lower(normalized_name))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_assignees_display_name_lower")
    op.execute("DROP INDEX IF EXISTS idx_assignees_normalized_name_lower")
    op.execute("DROP FUNCTION IF EXISTS normalize_assignee(text)")
