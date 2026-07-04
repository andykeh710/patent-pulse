"""V3.8I — Patent figures table + thumbnail_url + figures_status

Adds patent_figures for per-patent drawing storage, thumbnail_url to
PatentPublication for the first figure's thumbnail link, and figures_status
for tracking fetch state (pending/partial/complete/unavailable).

Revision ID: 0039
Revises: 0038
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "0039"
down_revision: Union[str, None] = "0038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── patent_figures ─────────────────────────────────────────
    op.create_table(
        "patent_figures",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "patent_id",
            sa.UUID(),
            sa.ForeignKey("patent_publications.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("full_path", sa.String(512), nullable=False),
        sa.Column("thumb_path", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(32), nullable=True),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("figure_label", sa.String(256), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_patent_figures_patent_ordinal", "patent_figures", ["patent_id", "ordinal"], unique=True)

    # ── patent_publications columns ─────────────────────────────
    op.add_column("patent_publications", sa.Column("thumbnail_url", sa.String(512), nullable=True))
    op.add_column(
        "patent_publications",
        sa.Column(
            "figures_status",
            sa.String(16),
            nullable=False,
            server_default="pending",
        ),
    )


def downgrade() -> None:
    op.drop_column("patent_publications", "figures_status")
    op.drop_column("patent_publications", "thumbnail_url")
    op.drop_index("ix_patent_figures_patent_ordinal", table_name="patent_figures")
    op.drop_table("patent_figures")
