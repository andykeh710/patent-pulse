import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, Float, Index, JSON, String, Text, func
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

    summary: Mapped[dict | None] = mapped_column(JSON)
    novel_applications: Mapped[list[str]] = mapped_column(JSONB, default=list)

    interesting_score: Mapped[float | None] = mapped_column(Float)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON)

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
    )

    def __repr__(self) -> str:
        return f"<PatentPublication {self.doc_id}>"
