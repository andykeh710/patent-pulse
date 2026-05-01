"""Phase 0: AI artifact layer, run history, single-user scaffold, side tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-28

Adds:
 - Columns on ``patent_publications``: legal_status_confidence, tags,
   interesting_score_version, opportunity_score(+_version, _breakdown),
   why_now_text, latest_{summary,tags,why_now}_artifact_id.
 - New tables: users, assignees, ai_runs, ai_artifacts,
   cross_industry_snapshots, patent_cliff_clusters, convergence_signals,
   trend_snapshots, sleeping_giant_clusters.
 - Seeds the single default user row.
 - Partial UNIQUE index on ai_artifacts(prompt_hash, input_hash,
   artifact_type) WHERE status='complete' for the content-addressed cache.
"""

from __future__ import annotations

import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Extend patent_publications
    # ------------------------------------------------------------------
    op.add_column(
        "patent_publications",
        sa.Column(
            "legal_status_confidence",
            sa.String(16),
            nullable=False,
            server_default="estimated",
        ),
    )
    op.add_column(
        "patent_publications",
        sa.Column("tags", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "patent_publications",
        sa.Column(
            "interesting_score_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "patent_publications",
        sa.Column("opportunity_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "patent_publications",
        sa.Column(
            "opportunity_score_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "patent_publications",
        sa.Column("opportunity_breakdown", sa.JSON(), nullable=True),
    )
    op.add_column(
        "patent_publications",
        sa.Column("why_now_text", sa.Text(), nullable=True),
    )
    # FKs to ai_artifacts are added after the table is created (below).
    op.add_column(
        "patent_publications",
        sa.Column("latest_summary_artifact_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "patent_publications",
        sa.Column("latest_tags_artifact_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "patent_publications",
        sa.Column("latest_why_now_artifact_id", sa.UUID(), nullable=True),
    )

    op.create_index(
        "ix_patent_publications_tags",
        "patent_publications",
        ["tags"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_patent_publications_opportunity_score",
        "patent_publications",
        ["opportunity_score"],
    )

    # ------------------------------------------------------------------
    # users (single-user scaffold)
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("email", sa.String(256), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("preferences", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )

    # Seed default user.
    default_user_id = os.getenv("DEFAULT_USER_ID", "local-user")
    default_user_display = os.getenv("DEFAULT_USER_DISPLAY_NAME", "Local User")
    op.execute(
        sa.text(
            "INSERT INTO users (id, display_name, is_admin) "
            "VALUES (:id, :name, true) ON CONFLICT (id) DO NOTHING"
        ).bindparams(id=default_user_id, name=default_user_display)
    )

    # ------------------------------------------------------------------
    # assignees
    # ------------------------------------------------------------------
    op.create_table(
        "assignees",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("normalized_name", sa.String(256), nullable=False),
        sa.Column("display_name", sa.String(256), nullable=False),
        sa.Column(
            "aliases", postgresql.JSONB(), nullable=False, server_default="[]"
        ),
        sa.Column("country", sa.String(8), nullable=True),
        sa.Column("entity_type", sa.String(32), nullable=True),
        sa.Column("patent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_assignees_normalized_name", "assignees", ["normalized_name"], unique=True
    )

    # ------------------------------------------------------------------
    # ai_runs
    # ------------------------------------------------------------------
    op.create_table(
        "ai_runs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("task_type", sa.String(32), nullable=False),
        sa.Column("run_mode", sa.String(16), nullable=False),
        sa.Column(
            "cohort_filter", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column("cohort_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cached_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uncached_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("prompt_name", sa.String(64), nullable=True),
        sa.Column("prompt_version", sa.Integer(), nullable=True),
        sa.Column(
            "est_input_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "est_output_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("est_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "actual_input_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "actual_output_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("actual_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "completed_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default="pending"
        ),
        sa.Column("celery_task_id", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.String(64),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ai_runs_task_type_status", "ai_runs", ["task_type", "status"])
    op.create_index("ix_ai_runs_created_at_desc", "ai_runs", ["created_at"])

    # ------------------------------------------------------------------
    # ai_artifacts
    # ------------------------------------------------------------------
    op.create_table(
        "ai_artifacts",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "patent_publication_id",
            sa.UUID(),
            sa.ForeignKey("patent_publications.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "run_id",
            sa.UUID(),
            sa.ForeignKey("ai_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("artifact_type", sa.String(32), nullable=False),
        sa.Column(
            "artifact_version", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("prompt_name", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False),
        sa.Column("prompt_hash", sa.String(64), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("subject_key", sa.String(128), nullable=True),
        sa.Column("content_json", postgresql.JSONB(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "output_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "estimated_cost_usd", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column(
            "actual_cost_usd", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default="pending"
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ai_artifacts_patent_publication_id",
        "ai_artifacts",
        ["patent_publication_id"],
    )
    op.create_index("ix_ai_artifacts_run_id", "ai_artifacts", ["run_id"])
    op.create_index(
        "ix_ai_artifacts_artifact_type", "ai_artifacts", ["artifact_type"]
    )
    op.create_index(
        "ix_ai_artifacts_prompt_hash", "ai_artifacts", ["prompt_hash"]
    )
    op.create_index("ix_ai_artifacts_input_hash", "ai_artifacts", ["input_hash"])
    op.create_index(
        "ix_ai_artifacts_subject_key",
        "ai_artifacts",
        ["subject_key", "artifact_type"],
    )
    op.create_index(
        "ix_ai_artifacts_patent_type_version",
        "ai_artifacts",
        ["patent_publication_id", "artifact_type", "artifact_version"],
    )
    op.create_index(
        "ix_ai_artifacts_prompt_input_hash",
        "ai_artifacts",
        ["prompt_hash", "input_hash", "artifact_type"],
    )
    op.create_index(
        "uq_ai_artifacts_cache_key",
        "ai_artifacts",
        ["prompt_hash", "input_hash", "artifact_type"],
        unique=True,
        postgresql_where=sa.text("status = 'complete'"),
    )
    op.create_index(
        "ix_ai_artifacts_created_at",
        "ai_artifacts",
        ["created_at"],
    )

    # Wire up the FK columns on patent_publications now that ai_artifacts exists.
    op.create_foreign_key(
        "fk_patent_latest_summary_artifact",
        "patent_publications",
        "ai_artifacts",
        ["latest_summary_artifact_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_patent_latest_tags_artifact",
        "patent_publications",
        "ai_artifacts",
        ["latest_tags_artifact_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_patent_latest_why_now_artifact",
        "patent_publications",
        "ai_artifacts",
        ["latest_why_now_artifact_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------------------------
    # cross_industry_snapshots
    # ------------------------------------------------------------------
    op.create_table(
        "cross_industry_snapshots",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "run_id",
            sa.UUID(),
            sa.ForeignKey("ai_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "patent_id",
            sa.UUID(),
            sa.ForeignKey("patent_publications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "neighbor_patent_id",
            sa.UUID(),
            sa.ForeignKey("patent_publications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("distance", sa.Float(), nullable=False),
        sa.Column(
            "different_industry",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "source_industries",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "neighbor_industries",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "patent_id", "neighbor_patent_id", name="uq_cross_industry_pair"
        ),
    )
    op.create_index(
        "ix_cross_industry_snapshots_patent_id",
        "cross_industry_snapshots",
        ["patent_id"],
    )
    op.create_index(
        "ix_cross_industry_snapshots_run_id",
        "cross_industry_snapshots",
        ["run_id"],
    )

    # ------------------------------------------------------------------
    # patent_cliff_clusters
    # ------------------------------------------------------------------
    op.create_table(
        "patent_cliff_clusters",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("key_type", sa.String(16), nullable=False),
        sa.Column("key_value", sa.String(256), nullable=False),
        sa.Column("window_months", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("patent_count", sa.Integer(), nullable=False),
        sa.Column(
            "representative_patent_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_patent_cliff_clusters_key_value",
        "patent_cliff_clusters",
        ["key_value"],
    )

    # ------------------------------------------------------------------
    # convergence_signals
    # ------------------------------------------------------------------
    op.create_table(
        "convergence_signals",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("cpc_a", sa.String(32), nullable=False),
        sa.Column("cpc_b", sa.String(32), nullable=False),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("window_months", sa.Integer(), nullable=False),
        sa.Column("joint_count", sa.Integer(), nullable=False),
        sa.Column("baseline_count", sa.Integer(), nullable=False),
        sa.Column("growth_ratio", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "cpc_a",
            "cpc_b",
            "window_start",
            "window_months",
            name="uq_convergence_pair_window",
        ),
    )
    op.create_index(
        "ix_convergence_signals_cpc_a", "convergence_signals", ["cpc_a"]
    )
    op.create_index(
        "ix_convergence_signals_cpc_b", "convergence_signals", ["cpc_b"]
    )

    # ------------------------------------------------------------------
    # trend_snapshots
    # ------------------------------------------------------------------
    op.create_table(
        "trend_snapshots",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("surface", sa.String(16), nullable=False),
        sa.Column("key", sa.String(256), nullable=False),
        sa.Column("week_start", sa.DateTime(), nullable=False),
        sa.Column("count_4w", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("count_12w", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "baseline_12mo", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column("z_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("growth_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "assignee_diversity", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column(
            "cpc_diversity", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column(
            "top_patent_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "surface", "key", "week_start", name="uq_trend_surface_key_week"
        ),
    )
    op.create_index("ix_trend_snapshots_surface", "trend_snapshots", ["surface"])
    op.create_index("ix_trend_snapshots_key", "trend_snapshots", ["key"])
    op.create_index(
        "ix_trend_snapshots_week_start", "trend_snapshots", ["week_start"]
    )

    # ------------------------------------------------------------------
    # sleeping_giant_clusters
    # ------------------------------------------------------------------
    op.create_table(
        "sleeping_giant_clusters",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("avg_age_years", sa.Float(), nullable=False),
        sa.Column("avg_interesting_score", sa.Float(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "representative_patent_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "linked_trend_snapshot_id",
            sa.UUID(),
            sa.ForeignKey("trend_snapshots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("sleeping_giant_clusters")
    op.drop_index("ix_trend_snapshots_week_start", table_name="trend_snapshots")
    op.drop_index("ix_trend_snapshots_key", table_name="trend_snapshots")
    op.drop_index("ix_trend_snapshots_surface", table_name="trend_snapshots")
    op.drop_table("trend_snapshots")
    op.drop_index("ix_convergence_signals_cpc_b", table_name="convergence_signals")
    op.drop_index("ix_convergence_signals_cpc_a", table_name="convergence_signals")
    op.drop_table("convergence_signals")
    op.drop_index(
        "ix_patent_cliff_clusters_key_value", table_name="patent_cliff_clusters"
    )
    op.drop_table("patent_cliff_clusters")
    op.drop_index(
        "ix_cross_industry_snapshots_run_id", table_name="cross_industry_snapshots"
    )
    op.drop_index(
        "ix_cross_industry_snapshots_patent_id",
        table_name="cross_industry_snapshots",
    )
    op.drop_table("cross_industry_snapshots")

    op.drop_constraint(
        "fk_patent_latest_why_now_artifact",
        "patent_publications",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_patent_latest_tags_artifact",
        "patent_publications",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_patent_latest_summary_artifact",
        "patent_publications",
        type_="foreignkey",
    )

    op.drop_index("ix_ai_artifacts_created_at", table_name="ai_artifacts")
    op.drop_index("uq_ai_artifacts_cache_key", table_name="ai_artifacts")
    op.drop_index("ix_ai_artifacts_prompt_input_hash", table_name="ai_artifacts")
    op.drop_index("ix_ai_artifacts_patent_type_version", table_name="ai_artifacts")
    op.drop_index("ix_ai_artifacts_subject_key", table_name="ai_artifacts")
    op.drop_index("ix_ai_artifacts_input_hash", table_name="ai_artifacts")
    op.drop_index("ix_ai_artifacts_prompt_hash", table_name="ai_artifacts")
    op.drop_index("ix_ai_artifacts_artifact_type", table_name="ai_artifacts")
    op.drop_index("ix_ai_artifacts_run_id", table_name="ai_artifacts")
    op.drop_index(
        "ix_ai_artifacts_patent_publication_id", table_name="ai_artifacts"
    )
    op.drop_table("ai_artifacts")

    op.drop_index("ix_ai_runs_created_at_desc", table_name="ai_runs")
    op.drop_index("ix_ai_runs_task_type_status", table_name="ai_runs")
    op.drop_table("ai_runs")

    op.drop_index("ix_assignees_normalized_name", table_name="assignees")
    op.drop_table("assignees")

    op.drop_table("users")

    op.drop_index(
        "ix_patent_publications_opportunity_score",
        table_name="patent_publications",
    )
    op.drop_index("ix_patent_publications_tags", table_name="patent_publications")

    op.drop_column("patent_publications", "latest_why_now_artifact_id")
    op.drop_column("patent_publications", "latest_tags_artifact_id")
    op.drop_column("patent_publications", "latest_summary_artifact_id")
    op.drop_column("patent_publications", "why_now_text")
    op.drop_column("patent_publications", "opportunity_breakdown")
    op.drop_column("patent_publications", "opportunity_score_version")
    op.drop_column("patent_publications", "opportunity_score")
    op.drop_column("patent_publications", "interesting_score_version")
    op.drop_column("patent_publications", "tags")
    op.drop_column("patent_publications", "legal_status_confidence")
