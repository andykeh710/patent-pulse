"""add_topic_fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-21

Add keywords, opportunity_tags, min_opportunity_score, and user_id columns
to the themes table. This extends the existing theme system to support
user-created topics alongside system/CPC-section themes.

Differentiation: user_id is NULL for system themes, non-NULL for user topics.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("themes", sa.Column("keywords", sa.JSON(), nullable=True))
    op.add_column("themes", sa.Column("opportunity_tags", sa.JSON(), nullable=True))
    op.add_column("themes", sa.Column("min_opportunity_score", sa.Float(), nullable=True))
    op.add_column("themes", sa.Column("user_id", sa.String(64), nullable=True))
    op.create_index("ix_themes_user_id", "themes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_themes_user_id", table_name="themes")
    op.drop_column("themes", "user_id")
    op.drop_column("themes", "min_opportunity_score")
    op.drop_column("themes", "opportunity_tags")
    op.drop_column("themes", "keywords")
