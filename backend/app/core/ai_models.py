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
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import Base

# ---------------------------------------------------------------------------
# Single-user scaffold
# ---------------------------------------------------------------------------


class User(Base):
    """User authentication and preferences."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(__import__("uuid").uuid4()))
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256))
    tier: Mapped[str] = mapped_column(String(16), default="free", index=True)
    # Security: users are NON-admin by default. Admin is granted only to
    # explicitly-known accounts (the DEFAULT_USER_ID scaffold and the
    # ADMIN_EMAILS allowlist). See migration 0035.
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    preferences: Mapped[dict | None] = mapped_column(JSONB)
    persona: Mapped[str | None] = mapped_column(String(16), nullable=True)
    industry_focus: Mapped[str | None] = mapped_column(String(64), nullable=True)
    interests_freetext: Mapped[str | None] = mapped_column(Text, nullable=True)
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_today_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    previous_today_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company_follows = relationship("UserCompanyFollow", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover - repr only
        return f"<User {self.id}>"


class UserCompanyFollow(Base):
    __tablename__ = "user_company_follows"

    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    company_normalized_name: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="company_follows")


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

    created_by: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
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
# Content drafts (Phase 4)
# ---------------------------------------------------------------------------


class ContentDraft(Base):
    """User-facing content generated from patents, topics, trends, or companies.

    user_id is a plain string (no FK) matching the WatchlistItem convention.
    The ``users`` table does not exist in root; auth is deferred to V1.1.
    """

    __tablename__ = "content_drafts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(
        String(64), index=True, default="anonymous"
    )
    source_type: Mapped[str] = mapped_column(
        String(16), index=True
    )  # "patent" | "topic" | "trend" | "company"
    source_id: Mapped[uuid.UUID] = mapped_column(index=True)
    content_type: Mapped[str] = mapped_column(
        String(32), index=True
    )  # "linkedin_post" | "content_idea"
    content_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16), default="draft", server_default="draft"
    )
    prompt_hash: Mapped[str | None] = mapped_column(String(64))
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_artifacts.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, onupdate=datetime.utcnow, server_default="now()"
    )


# ---------------------------------------------------------------------------
# Expiry assessments (Sprint 2A)
# ---------------------------------------------------------------------------


class ExpiryAssessment(Base):
    """Deterministic expiry assessment derived from PatentPublication fields.

    This is a derived layer — does not replace the raw source columns
    (legal_status, estimated_expiry_date, maintenance_status, etc.).
    Recomputed idempotently by the backfill task.
    """

    __tablename__ = "expiry_assessments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patent_publication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patent_publications.id", ondelete="CASCADE"),
        index=True,
    )

    estimated_expiry_date: Mapped[date | None] = mapped_column(Date)

    expiry_status: Mapped[str] = mapped_column(
        String(32), default="unknown", server_default="unknown"
    )
    expiry_status_confidence: Mapped[str] = mapped_column(
        String(16), default="low", server_default="low"
    )

    maintenance_status: Mapped[str] = mapped_column(
        String(32), default="unknown", server_default="unknown"
    )
    maintenance_status_source: Mapped[str | None] = mapped_column(String(64))

    active_family_risk: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    active_family_risk_reason: Mapped[str | None] = mapped_column(Text)

    terminal_disclaimer_flag: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    patent_term_adjustment_days: Mapped[int | None] = mapped_column(Integer)

    legal_caveats: Mapped[list[str]] = mapped_column(JSONB, default=list)

    assessment_json: Mapped[dict | None] = mapped_column(JSONB)

    # Sprint 2B: expiry-specific opportunity scoring (deterministic, not LLM).
    expiry_opportunity_score: Mapped[float | None] = mapped_column(Float)
    expiry_opportunity_breakdown: Mapped[dict | None] = mapped_column(JSONB)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="now()"
    )
    source_updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default="now()"
    )


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


# ---------------------------------------------------------------------------
# Sprint 5 — Commercial Usage Signals
# ---------------------------------------------------------------------------


class UsageEvidence(Base):
    """One row per piece of usage evidence. Multiple rows per patent."""

    __tablename__ = "usage_evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    patent_publication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patent_publications.id", ondelete="CASCADE")
    )
    source_type: Mapped[str] = mapped_column(String(32))
    source_patent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patent_publications.id", ondelete="SET NULL")
    )
    source_patent_doc_id: Mapped[str | None] = mapped_column(String(64))
    source_patent_title: Mapped[str | None] = mapped_column(Text)
    source_patent_assignee: Mapped[str | None] = mapped_column(Text)
    source_patent_filing_date: Mapped[date | None] = mapped_column(Date)
    source_patent_cpc: Mapped[list[str]] = mapped_column(JSONB, default=list)
    matched_cpc: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    cpc_overlap_count: Mapped[int] = mapped_column(Integer, default=0)
    similarity_score: Mapped[float | None] = mapped_column(Float)
    citation_direction: Mapped[str | None] = mapped_column(String(16))
    evidence_tier: Mapped[str] = mapped_column(String(8))
    evidence_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )

    __table_args__ = (
        Index("ix_usage_evidence_patent", "patent_publication_id"),
        Index("ix_usage_evidence_source_type", "source_type"),
        Index("ix_usage_evidence_tier", "evidence_tier"),
        Index("ix_usage_evidence_source_patent", "source_patent_id"),
        Index(
            "ix_usage_evidence_patent_tier",
            "patent_publication_id",
            "evidence_tier",
        ),
    )


class PatentUsageSignals(Base):
    """One row per assessed patent. Aggregates evidence into score + summary."""

    __tablename__ = "patent_usage_signals"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    patent_publication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patent_publications.id", ondelete="CASCADE")
    )
    usage_signal_score: Mapped[float | None] = mapped_column(Float)
    usage_signal_confidence: Mapped[str | None] = mapped_column(String(8))
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    strong_evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    weak_evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    strongest_evidence_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True))
    )
    market_categories: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    top_companies: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    most_recent_evidence_date: Mapped[date | None] = mapped_column(Date)
    narrative_summary: Mapped[str | None] = mapped_column(Text)
    narrative_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_artifacts.id", ondelete="SET NULL")
    )
    narrative_generated_at: Mapped[datetime | None] = mapped_column(DateTime)
    has_self_citation_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    has_stale_evidence_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default="now()"
    )

    __table_args__ = (
        Index("ix_usage_signals_patent", "patent_publication_id", unique=True),
        Index("ix_usage_signals_score", "usage_signal_score"),
        Index("ix_usage_signals_confidence", "usage_signal_confidence"),
    )
