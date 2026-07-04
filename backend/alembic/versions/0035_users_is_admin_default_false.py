"""Default users.is_admin to false and demote non-allowlisted users.

Security fix (P0): previously the users.is_admin column defaulted to TRUE
(both model default and DB server_default). Every account — including every
magic-link signup — silently became an admin, so admin-only endpoints were
effectively open to anyone who could sign in.

This migration:
  1. Flips the column default to FALSE so new accounts are non-admin.
  2. Demotes every existing user to non-admin, then re-grants admin ONLY to
     explicitly-known accounts:
       - the configured DEFAULT_USER_ID single-user scaffold account, and
       - any address in the ADMIN_EMAILS env allowlist (comma-separated,
         case-insensitive).

Set ADMIN_EMAILS before running in any shared environment so the intended
admins keep their access. If neither is set in production, NO user remains
admin — a safe-by-default outcome (better than everyone-admin); promote the
real admin afterwards via ADMIN_EMAILS + re-login, or a one-off UPDATE.
"""

from __future__ import annotations

import os

import sqlalchemy as sa

from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def _admin_emails() -> list[str]:
    raw = os.getenv("ADMIN_EMAILS", "")
    return [e.strip().lower() for e in raw.split(",") if e.strip()]


def upgrade() -> None:
    # 1. New users are non-admin by default.
    op.execute("ALTER TABLE users ALTER COLUMN is_admin SET DEFAULT false")

    # 2. Demote everyone first (closes the open-admin hole), then re-grant
    #    only to explicitly-known admins.
    op.execute("UPDATE users SET is_admin = false")

    default_user_id = os.getenv("DEFAULT_USER_ID", "local-user")
    op.execute(
        sa.text("UPDATE users SET is_admin = true WHERE id = :uid").bindparams(uid=default_user_id)
    )

    for email in _admin_emails():
        op.execute(
            sa.text("UPDATE users SET is_admin = true WHERE lower(email) = :e").bindparams(e=email)
        )


def downgrade() -> None:
    # Restore the prior (insecure) default only. We deliberately do NOT
    # re-grant blanket admin to previously-demoted users: that data is not
    # recoverable and doing so would reintroduce the vulnerability.
    op.execute("ALTER TABLE users ALTER COLUMN is_admin SET DEFAULT true")
