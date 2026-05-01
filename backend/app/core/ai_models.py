"""
Phase 0 models: durable AI artifact layer + run history + supporting tables.

Design decisions (from the V1 plan):
 - ``AIArtifact`` stores ONLY LLM-produced outputs. Pure-rules outputs
   (interesting_score, opportunity_score, rules-based cliff clusters) live
   as columns or in dedicated side tables below.
 - ``AIRun`` records every admin-initiated batch execution with cost
   estimate/actual and artifact counts.
 - ``User`` exists with a single seeded row (``settings.default_user_id``)
   so single-user V1 has stable FKs; V1.1 auth is purely additive.
 - ``Assignee`` is a normalized entity used by Phase 1+ opportunity-scoring
   and Phase 3.7 Assignee Strategy. Free-text ``PatentPublication.assignees``
   remains for backcompat until backfill is run.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base

# ---------------------------------------------------------------------------
# Single-user scaffold
# ---------------------------------------------------------------------------


class User(Base):
    """
    Single-user scaffold. Phase 0 seeds exactly one row matching
    ``settings.default_user_id``. V1.1 auth makes this multi-user.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128))
    email: Mapped[str | None] = mapped_column(String(256))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    preferences: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover - repr only
        return f"<User {self.id}>"


# ---------------------------------------------------------------------------
# Assignee normalization
# ---------------------------------------------------------------------------


class Assignee(Base):
    """
    Normalized assignee. Populated by a one-shot backfill from
    ``PatentPublication.assignees``.
    """

    __tablename__ = "assignees"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    normalized_name: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(256))
    aliases: Mapped[list[str]] = mapped_column(JSONB, default=list)
    country: Mapped[str | None] = mapped_column(String(8))
    entity_type: Mapped[str | None] = mapped_column(String(32))  # corporation|university|sme|individual|gov
    patent_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# AI Runs + Artifacts
# ---------------------------------------------------------------------------

# Valid artifact types. Keep in sync with ``/admin/ai-runs`` task selector
# and the ``ARTIFACT_TYPE_TIER`` map in ``app.ai.llm_client``.
#
# LLM outputs:        summary, tags, why_now, opportunity_narrative,
#                     trend_narrative, assignee_narrative, score_rerank
# Rules-based scores: interesting_score, opportunity_score
ARTIFACT_TYPES = (
    "summary",
    "tags",
    "why_now",
    "opportunity_narrative",
    "trend_narrative",
    "assignee_narrative",
    "score_rerank",
    "interesting_score",
    "opportunity_score",
)

# Subset that is produced by deterministic rules (no LLM call). Cost is 0
# but every recompute still writes an AIArtifact row for audit + cache.
RULES_ARTIFACT_TYPES = ("interesting_score", "opportunity_score")

# Valid run modes. Enforced in ``/admin/ai-runs`` endpoint.
RUN_MODES = ("dev_fixture", "sample", "cohort", "full_batch")

# Valid statuses for both AIArtifact and AIRun.
ARTIFACT_STATUSES = ("pending", "complete", "failed")
RUN_STATUSES = ("pending", "running", "succeeded", "failed", "cancelled")


class AIRun(Base):
    """
    Record of a single admin-initiated AI batch. Every AIArtifact created by
    an ``ai_runs``-initiated task references the parent run; ad-hoc
    on-demand calls (e.g. a user clicking "Generate Why Now") have
    ``run_id=NULL`` on the produced artifact.
    """

    __tablename__ = "ai_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_type: Mapped[str] = mapped_column(String(32), index=True)  # one of ARTIFACT_TYPES
    run_mode: Mapped[str] = mapped_column(String(16))  # one of RUN_MODES
    cohort_filter: Mapped[dict] = mapped_column(JSONB, default=dict)
    cohort_size: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cached_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    uncached_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    model: Mapped[str] = mapped_column(String(64))
    prompt_name: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[int | None] = mapped_column(Integer)

    est_input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    est_output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    est_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    actual_input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    actual_output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    actual_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")

    completed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    celery_task_id: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)

    created_by: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()", index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        Index("ix_ai_runs_task_type_status", "task_type", "status"),
        Index("ix_ai_runs_created_at_desc", "created_at"),
    )


class AIArtifact(Base):
    """
    Durable record of a single LLM output.

    Keyed by ``(prompt_hash, input_hash)`` UNIQUE where ``status='complete'``
    so cache hits are fast and deterministic. Multiple in-flight ``pending``
    rows for the same input are tolerated but won't collide with completions.
    """

    __tablename__ = "ai_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Nullable for non-per-patent artifacts (trend_narrative, assignee_narrative).
    patent_publication_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patent_publications.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Nullable so on-demand calls (not created by /admin/ai-runs) work.
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    artifact_type: Mapped[str] = mapped_column(String(32), index=True)
    artifact_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    model: Mapped[str] = mapped_column(String(64))
    prompt_name: Mapped[str] = mapped_column(String(64))
    prompt_version: Mapped[int] = mapped_column(Integer)
    prompt_hash: Mapped[str] = mapped_column(String(64), index=True)
    input_hash: Mapped[str] = mapped_column(String(64), index=True)

    # Free-form subject identifier for non-patent artifacts (e.g. assignee id
    # or "cpc:G06F". Included in input_hash calculation for uniqueness.)
    # NOTE: composite index with artifact_type is declared in __table_args__;
    # do not also use index=True here or SA generates a duplicate-named index.
    subject_key: Mapped[str | None] = mapped_column(String(128))

    content_json: Mapped[dict | None] = mapped_column(JSONB)
    content_text: Mapped[str | None] = mapped_column(Text)

    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    actual_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")

    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()", index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default="now()"
    )

    __table_args__ = (
        # Fast "latest N artifacts of type T for patent P" read.
        Index(
            "ix_ai_artifacts_patent_type_version",
            "patent_publication_id",
            "artifact_type",
            "artifact_version",
        ),
        # Content-addressed cache key. We index the triple; uniqueness is
        # enforced at the migration level with a WHERE status='complete'
        # partial unique index (not expressible cleanly via Index()).
        Index(
            "ix_ai_artifacts_prompt_input_hash",
            "prompt_hash",
            "input_hash",
            "artifact_type",
        ),
        Index("ix_ai_artifacts_subject_key", "subject_key", "artifact_type"),
    )


# ---------------------------------------------------------------------------
# Side tables for non-LLM creative-intelligence outputs
# ---------------------------------------------------------------------------


class CrossIndustrySnapshot(Base):
    """
    Per-cohort snapshot of cross-industry kNN neighbors for a patent.
    Regenerated by each cross-industry AIRun (pure embeddings, no LLM).
    """

    __tablename__ = "cross_industry_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    patent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patent_publications.id", ondelete="CASCADE"), index=True
    )
    neighbor_patent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patent_publications.id", ondelete="CASCADE"), index=True
    )
    distance: Mapped[float] = mapped_column(Float)
    different_industry: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    source_industries: Mapped[list[str]] = mapped_column(JSONB, default=list)
    neighbor_industries: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )

    __table_args__ = (
        UniqueConstraint(
            "patent_id",
            "neighbor_patent_id",
            name="uq_cross_industry_pair",
        ),
    )


class PatentCliffCluster(Base):
    """Cluster of expiring patents sharing a CPC/tag/assignee/embedding."""

    __tablename__ = "patent_cliff_clusters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key_type: Mapped[str] = mapped_column(String(16))  # cpc|tag|assignee|embedding
    key_value: Mapped[str] = mapped_column(String(256), index=True)
    window_months: Mapped[int] = mapped_column(Integer)  # 6|12|24|60
    window_start: Mapped[datetime] = mapped_column(DateTime)
    patent_count: Mapped[int] = mapped_column(Integer)
    representative_patent_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )


class ConvergenceSignal(Base):
    """(CPC_A, CPC_B) joint-filing growth rate."""

    __tablename__ = "convergence_signals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cpc_a: Mapped[str] = mapped_column(String(32), index=True)
    cpc_b: Mapped[str] = mapped_column(String(32), index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime)
    window_months: Mapped[int] = mapped_column(Integer)
    joint_count: Mapped[int] = mapped_column(Integer)
    baseline_count: Mapped[int] = mapped_column(Integer)
    growth_ratio: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )

    __table_args__ = (
        UniqueConstraint(
            "cpc_a",
            "cpc_b",
            "window_start",
            "window_months",
            name="uq_convergence_pair_window",
        ),
    )


class TrendSnapshot(Base):
    """
    Weekly trend row. ``surface`` = theme|tag|cpc|assignee; ``key`` is the
    surface-specific identifier (e.g. the theme UUID as string, the tag
    string, the CPC prefix, or the assignee UUID as string).
    """

    __tablename__ = "trend_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    surface: Mapped[str] = mapped_column(String(16), index=True)
    key: Mapped[str] = mapped_column(String(256), index=True)
    week_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    count_4w: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    count_12w: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    baseline_12mo: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    z_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    growth_pct: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    assignee_diversity: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    cpc_diversity: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    top_patent_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )

    __table_args__ = (
        UniqueConstraint(
            "surface",
            "key",
            "week_start",
            name="uq_trend_surface_key_week",
        ),
    )


class SleepingGiantCluster(Base):
    """Cluster of old-but-high-interest patents linked to a current trend."""

    __tablename__ = "sleeping_giant_clusters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    avg_age_years: Mapped[float] = mapped_column(Float)
    avg_interesting_score: Mapped[float] = mapped_column(Float)
    size: Mapped[int] = mapped_column(Integer)
    representative_patent_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    linked_trend_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trend_snapshots.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )
