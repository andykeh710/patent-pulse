import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PatentPublication(Base):
    __tablename__ = "patent_publications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    doc_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    family_id: Mapped[str | None] = mapped_column(String(64), index=True)

    office: Mapped[str] = mapped_column(String(8))
    publication_number: Mapped[str] = mapped_column(String(32), index=True)
    application_number: Mapped[str | None] = mapped_column(String(32))
    kind_code: Mapped[str | None] = mapped_column(String(4))

    filing_date: Mapped[date | None] = mapped_column(Date)
    priority_date: Mapped[date | None] = mapped_column(Date)
    publication_date: Mapped[date | None] = mapped_column(Date, index=True)
    grant_date: Mapped[date | None] = mapped_column(Date)

    assignees: Mapped[list[str]] = mapped_column(JSONB, default=list)
    inventors: Mapped[list[str]] = mapped_column(JSONB, default=list)

    cpc: Mapped[list[str]] = mapped_column(JSONB, default=list)
    ipc: Mapped[list[str]] = mapped_column(JSONB, default=list)

    title: Mapped[str | None] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text)
    claims_text: Mapped[str | None] = mapped_column(Text)
    description_text: Mapped[str | None] = mapped_column(Text)

    citations_backward: Mapped[list[str]] = mapped_column(JSONB, default=list)
    family_members: Mapped[list[str]] = mapped_column(JSONB, default=list)

    legal_status: Mapped[str | None] = mapped_column(String(32))
    maintenance_status: Mapped[str | None] = mapped_column(String(32))
    estimated_expiry_date: Mapped[date | None] = mapped_column(Date, index=True)

    # Phase 0: legal-confidence honest. V1 always "estimated"; V1.1 flips to
    # "confirmed" when INPADOC reconciliation lands.
    legal_status_confidence: Mapped[str] = mapped_column(
        String(16), default="estimated", server_default="estimated"
    )

    summary: Mapped[dict | None] = mapped_column(JSON)
    novel_applications: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Phase 1: structured tags (industries, problem_solved, ...). Mirror of
    # the latest AIArtifact(tags).content_json for fast querying.
    tags: Mapped[dict | None] = mapped_column(JSONB)

    interesting_score: Mapped[float | None] = mapped_column(Float)
    interesting_score_version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1"
    )
    score_breakdown: Mapped[dict | None] = mapped_column(JSON)

    # Phase 1: Opportunity score (pure-rules in Phase 1, LLM re-rank in Phase 4).
    opportunity_score: Mapped[float | None] = mapped_column(Float)
    opportunity_score_version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1"
    )
    opportunity_breakdown: Mapped[dict | None] = mapped_column(JSON)

    # Phase 4: Why Now narrative. Mirror of latest AIArtifact(why_now).content_text.
    why_now_text: Mapped[str | None] = mapped_column(Text)

    # Phase 4: Presentation rank (LLM re-rank in Phase 4, rules fallback in Phase 1–3).
    presentation_rank_score: Mapped[float | None] = mapped_column(Float)
    presentation_rank_reason: Mapped[str | None] = mapped_column(Text)
    presentation_rank_confidence: Mapped[str | None] = mapped_column(String(16))
    presentation_rank_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "ai_artifacts.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_pp_presentation_rank_artifact_id",
        ),
        nullable=True,
    )

    # Denormalized "latest artifact" pointers. Nullable FKs; kept as
    # untyped UUIDs to avoid a circular import with ai_models at module-load.
    # ``use_alter=True`` is required because ai_artifacts also FKs back to
    # patent_publications, creating a cycle that SQLAlchemy cannot resolve
    # at create_all/drop_all time without ALTER TABLE.
    latest_summary_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "ai_artifacts.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_pp_latest_summary_artifact_id",
        ),
        nullable=True,
    )
    latest_tags_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "ai_artifacts.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_pp_latest_tags_artifact_id",
        ),
        nullable=True,
    )
    latest_why_now_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "ai_artifacts.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_pp_latest_why_now_artifact_id",
        ),
        nullable=True,
    )

    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))

    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)

    raw_data: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    summarized_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        Index("ix_patent_publications_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_patent_publications_cpc", "cpc", postgresql_using="gin"),
        Index("ix_patent_publications_assignees", "assignees", postgresql_using="gin"),
        Index("ix_patent_publications_tags", "tags", postgresql_using="gin"),
        Index("ix_patent_publications_opportunity_score", "opportunity_score"),
    )

    def __repr__(self) -> str:
        return f"<PatentPublication {self.doc_id}>"
