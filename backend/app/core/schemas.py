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
    legal_status_confidence: str = "estimated"
    interesting_score: float | None = None
    opportunity_score: float | None = None
    tags: dict | None = None
    summary_what_it_is: str | None = None
    estimated_expiry_date: date | None = None
    days_until_expiry: int | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_patent(cls, patent: Any) -> "PatentListItem":
        summary_what = None
        if patent.summary and isinstance(patent.summary, dict):
            summary_what = patent.summary.get("what_it_is")

        days_until = None
        if patent.estimated_expiry_date:
            delta = patent.estimated_expiry_date - date.today()
            days_until = delta.days

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
            legal_status_confidence=getattr(
                patent, "legal_status_confidence", None
            ) or "estimated",
            interesting_score=patent.interesting_score,
            opportunity_score=getattr(patent, "opportunity_score", None),
            tags=getattr(patent, "tags", None),
            summary_what_it_is=summary_what,
            estimated_expiry_date=patent.estimated_expiry_date,
            days_until_expiry=days_until,
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
    claims_text: str | None = None
    legal_status: str | None = None
    legal_status_confidence: str = "estimated"
    maintenance_status: str | None = None
    estimated_expiry_date: date | None = None
    summary: SummarySchema | None = None
    novel_applications: list[str] = []
    interesting_score: float | None = None
    score_breakdown: ScoreBreakdown | None = None
    opportunity_score: float | None = None
    opportunity_score_version: int | None = None
    opportunity_breakdown: dict | None = None
    tags: dict | None = None
    why_now_text: str | None = None
    family_members: list[str] = []
    citations_backward: list[str] = []
    citations_forward: list[str] = []
    summarized_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    presentation_rank_score: float | None = None
    presentation_rank_reason: str | None = None
    presentation_rank_confidence: str | None = None

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
            claims_text=patent.claims_text,
            legal_status=patent.legal_status,
            legal_status_confidence=getattr(
                patent, "legal_status_confidence", None
            ) or "estimated",
            maintenance_status=patent.maintenance_status,
            estimated_expiry_date=patent.estimated_expiry_date,
            summary=summary,
            novel_applications=patent.novel_applications or [],
            interesting_score=patent.interesting_score,
            score_breakdown=score_breakdown,
            opportunity_score=getattr(patent, "opportunity_score", None),
            opportunity_score_version=getattr(patent, "opportunity_score_version", None),
            opportunity_breakdown=getattr(patent, "opportunity_breakdown", None),
            tags=getattr(patent, "tags", None),
            why_now_text=getattr(patent, "why_now_text", None),
            family_members=patent.family_members or [],
            citations_backward=patent.citations_backward or [],
            citations_forward=patent.citations_forward or [],
            summarized_at=patent.summarized_at,
            created_at=patent.created_at,
            updated_at=patent.updated_at,
            presentation_rank_score=getattr(patent, "presentation_rank_score", None),
            presentation_rank_reason=getattr(patent, "presentation_rank_reason", None),
            presentation_rank_confidence=getattr(patent, "presentation_rank_confidence", None),
        )


class ExpiryItem(BaseModel):
    id: UUID
    doc_id: str
    title: str | None = None
    assignees: list[str] = []
    estimated_expiry_date: date | None = None
    days_until_expiry: int | None = None
    legal_status: str | None = None
    legal_status_confidence: str = "estimated"
    opportunity_score: float | None = None
    tags: dict | None = None

    # Sprint 2B: assessment-enriched fields from ExpiryAssessment LEFT JOIN.
    expiry_status: str | None = None
    expiry_status_confidence: str | None = None
    active_family_risk: bool | None = None
    maintenance_status: str | None = None
    expiry_opportunity_score: float | None = None

    # Sprint 2C: CSV export fields.
    publication_number: str | None = None
    office: str | None = None

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
    days_ahead: int = Field(default=365, ge=1, le=7300)
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
    within_5_years: int
    within_10_years: int
    within_20_years: int
    total_with_expiry: int


class TrendPoint(BaseModel):
    period: str
    count: int


class TrendResponse(BaseModel):
    points: list[TrendPoint]


class FreshnessResponse(BaseModel):
    latest_patent_created_at: datetime | None
    latest_patent_publication_date: str | None
    latest_summarized_at: datetime | None
    latest_trend_snapshot_at: datetime | None
    latest_ai_run_at: datetime | None
    total_patents: int
    total_summarized: int
    total_trend_snapshots: int
