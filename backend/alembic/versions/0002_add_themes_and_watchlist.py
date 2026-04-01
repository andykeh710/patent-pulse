"""Add themes and watchlist tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "themes",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cpc_prefixes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("assignee_keywords", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("title_keywords", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_themes_name", "themes", ["name"], unique=True)

    op.create_table(
        "theme_matches",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("theme_id", sa.UUID(), sa.ForeignKey("themes.id"), nullable=False),
        sa.Column(
            "patent_id",
            sa.UUID(),
            sa.ForeignKey("patent_publications.id"),
            nullable=False,
        ),
        sa.Column("match_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("match_reasons", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("matched_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_theme_matches_theme_id", "theme_matches", ["theme_id"])
    op.create_index("ix_theme_matches_patent_id", "theme_matches", ["patent_id"])
    op.create_index(
        "ix_theme_matches_unique",
        "theme_matches",
        ["theme_id", "patent_id"],
        unique=True,
    )

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column(
            "patent_id",
            sa.UUID(),
            sa.ForeignKey("patent_publications.id"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("added_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_watchlist_items_user_id", "watchlist_items", ["user_id"])
    op.create_index("ix_watchlist_items_patent_id", "watchlist_items", ["patent_id"])
    op.create_index(
        "ix_watchlist_items_unique",
        "watchlist_items",
        ["user_id", "patent_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("watchlist_items")
    op.drop_table("theme_matches")
    op.drop_table("themes")
