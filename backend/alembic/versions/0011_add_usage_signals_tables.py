"""add_usage_signals_tables

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-23

Adds usage_evidence and patent_usage_signals tables for Sprint 5
Commercial Usage Signals MVP.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── usage_evidence ─────────────────────────────────────────────
    op.create_table(
        "usage_evidence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "patent_publication_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patent_publications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column(
            "source_patent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patent_publications.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_patent_doc_id", sa.String(64), nullable=True),
        sa.Column("source_patent_title", sa.Text, nullable=True),
        sa.Column("source_patent_assignee", sa.Text, nullable=True),
        sa.Column("source_patent_filing_date", sa.Date, nullable=True),
        sa.Column(
            "source_patent_cpc",
            postgresql.JSONB,
            server_default="[]",
            nullable=False,
        ),
        sa.Column("matched_cpc", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("cpc_overlap_count", sa.Integer, server_default="0"),
        sa.Column("similarity_score", sa.Float, nullable=True),
        sa.Column("citation_direction", sa.String(16), nullable=True),
        sa.Column("evidence_tier", sa.String(8), nullable=False),
        sa.Column(
            "evidence_confidence",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "retrieved_at",
            sa.DateTime,
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_usage_evidence_patent",
        "usage_evidence",
        ["patent_publication_id"],
    )
    op.create_index(
        "ix_usage_evidence_source_type",
        "usage_evidence",
        ["source_type"],
    )
    op.create_index(
        "ix_usage_evidence_tier",
        "usage_evidence",
        ["evidence_tier"],
    )
    op.create_index(
        "ix_usage_evidence_source_patent",
        "usage_evidence",
        ["source_patent_id"],
    )
    op.create_index(
        "ix_usage_evidence_patent_tier",
        "usage_evidence",
        ["patent_publication_id", "evidence_tier"],
    )

    # ── patent_usage_signals ───────────────────────────────────────
    op.create_table(
        "patent_usage_signals",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "patent_publication_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patent_publications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("usage_signal_score", sa.Float, nullable=True),
        sa.Column("usage_signal_confidence", sa.String(8), nullable=True),
        sa.Column("score_breakdown", postgresql.JSONB, nullable=True),
        sa.Column("evidence_count", sa.Integer, server_default="0"),
        sa.Column("strong_evidence_count", sa.Integer, server_default="0"),
        sa.Column("medium_evidence_count", sa.Integer, server_default="0"),
        sa.Column("weak_evidence_count", sa.Integer, server_default="0"),
        sa.Column(
            "strongest_evidence_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=True,
        ),
        sa.Column(
            "market_categories",
            postgresql.ARRAY(sa.Text),
            nullable=True,
        ),
        sa.Column(
            "top_companies",
            postgresql.ARRAY(sa.Text),
            nullable=True,
        ),
        sa.Column("most_recent_evidence_date", sa.Date, nullable=True),
        sa.Column("narrative_summary", sa.Text, nullable=True),
        sa.Column(
            "narrative_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_artifacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("narrative_generated_at", sa.DateTime, nullable=True),
        sa.Column(
            "has_self_citation_risk",
            sa.Boolean,
            server_default="false",
        ),
        sa.Column(
            "has_stale_evidence_risk",
            sa.Boolean,
            server_default="false",
        ),
        sa.Column(
            "computed_at",
            sa.DateTime,
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_usage_signals_patent",
        "patent_usage_signals",
        ["patent_publication_id"],
        unique=True,
    )
    op.create_index(
        "ix_usage_signals_score",
        "patent_usage_signals",
        ["usage_signal_score"],
    )
    op.create_index(
        "ix_usage_signals_confidence",
        "patent_usage_signals",
        ["usage_signal_confidence"],
    )


def downgrade() -> None:
    op.drop_table("patent_usage_signals")
    op.drop_table("usage_evidence")
