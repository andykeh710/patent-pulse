from datetime import date, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class SummarySchema(BaseModel):
    what_it_is: str
    problem_solved: str
    how_it_works: str
    commercial_significance: str
    who_should_care: list[str]
    novel_applications: list[dict[str, str]]
    confidence_note: str
    source_spans: list[dict[str, str]]


class ScoreBreakdown(BaseModel):
    cpc_relevance: float
    assignee_notoriety: float
    claim_breadth: float
    family_breadth: float
    semantic_novelty: float


class PatentListItem(BaseModel):
    id: UUID
    doc_id: str
    publication_number: str
    title: str | None = None
    assignees: list[str] = []
    cpc: list[str] = []
    publication_date: date | None = None
    grant_date: date | None = None
    legal_status: str | None = None
    interesting_score: float | None = None
    summary_what_it_is: str | None = None
    estimated_expiry_date: date | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_patent(cls, patent: Any) -> "PatentListItem":
        summary_what = None
        if patent.summary and isinstance(patent.summary, dict):
            summary_what = patent.summary.get("what_it_is")

        return cls(
            id=patent.id,
            doc_id=patent.doc_id,
            publication_number=patent.publication_number,
            title=patent.title,
            assignees=patent.assignees or [],
            cpc=patent.cpc or [],
            publication_date=patent.publication_date,
            grant_date=patent.grant_date,
            legal_status=patent.legal_status,
            interesting_score=patent.interesting_score,
            summary_what_it_is=summary_what,
            estimated_expiry_date=patent.estimated_expiry_date,
        )


class PatentDetailResponse(BaseModel):
    id: UUID
    doc_id: str
    family_id: str | None = None
    office: str
    publication_number: str
    application_number: str | None = None
    kind_code: str | None = None
    filing_date: date | None = None
    priority_date: date | None = None
    publication_date: date | None = None
    grant_date: date | None = None
    assignees: list[str] = []
    inventors: list[str] = []
    cpc: list[str] = []
    ipc: list[str] = []
    title: str | None = None
    abstract: str | None = None
    legal_status: str | None = None
    maintenance_status: str | None = None
    estimated_expiry_date: date | None = None
    summary: SummarySchema | None = None
    novel_applications: list[str] = []
    interesting_score: float | None = None
    score_breakdown: ScoreBreakdown | None = None
    family_members: list[str] = []
    citations_backward: list[str] = []
    summarized_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_patent(cls, patent: Any) -> "PatentDetailResponse":
        summary = None
        if patent.summary and isinstance(patent.summary, dict):
            summary = SummarySchema(**patent.summary)

        score_breakdown = None
        if patent.score_breakdown and isinstance(patent.score_breakdown, dict):
            score_breakdown = ScoreBreakdown(**patent.score_breakdown)

        return cls(
            id=patent.id,
            doc_id=patent.doc_id,
            family_id=patent.family_id,
            office=patent.office,
            publication_number=patent.publication_number,
            application_number=patent.application_number,
            kind_code=patent.kind_code,
            filing_date=patent.filing_date,
            priority_date=patent.priority_date,
            publication_date=patent.publication_date,
            grant_date=patent.grant_date,
            assignees=patent.assignees or [],
            inventors=patent.inventors or [],
            cpc=patent.cpc or [],
            ipc=patent.ipc or [],
            title=patent.title,
            abstract=patent.abstract,
            legal_status=patent.legal_status,
            maintenance_status=patent.maintenance_status,
            estimated_expiry_date=patent.estimated_expiry_date,
            summary=summary,
            novel_applications=patent.novel_applications or [],
            interesting_score=patent.interesting_score,
            score_breakdown=score_breakdown,
            family_members=patent.family_members or [],
            citations_backward=patent.citations_backward or [],
            summarized_at=patent.summarized_at,
            created_at=patent.created_at,
            updated_at=patent.updated_at,
        )


class ExpiryItem(BaseModel):
    id: UUID
    doc_id: str
    title: str | None = None
    assignees: list[str] = []
    estimated_expiry_date: date | None = None
    days_until_expiry: int | None = None
    legal_status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class PatentListParams(BaseModel):
    office: str | None = None
    kind_code: str | None = None
    cpc_prefix: str | None = None
    assignee: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    min_score: float | None = None
    sort_by: str = "publication_date"
    sort_order: str = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchParams(BaseModel):
    q: str
    cpc: str | None = None
    assignee: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ExpiryParams(BaseModel):
    days_ahead: int = Field(default=365, ge=1, le=3650)
    office: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TriggerIngestRequest(BaseModel):
    type: str = Field(..., pattern="^(grants|applications)$")
    target_date: date | None = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Any | None = None


class StatsResponse(BaseModel):
    total_patents: int
    total_grants: int
    total_applications: int
    summarized_count: int
    patents_this_week: int
    top_cpc_sections: list[dict[str, Any]]
    top_assignees: list[dict[str, Any]]


class ExpirySummary(BaseModel):
    within_30_days: int
    within_90_days: int
    within_365_days: int


class TrendPoint(BaseModel):
    period: str
    count: int


class TrendResponse(BaseModel):
    points: list[TrendPoint]
