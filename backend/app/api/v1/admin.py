from datetime import date
from typing import Any, Literal

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AppSettings, DbSession
from app.config import settings
from app.core.schemas import TaskStatusResponse
from app.tasks.celery_app import celery_app
from app.tasks.ingest_applications import ingest_weekly_applications
from app.tasks.ingest_grants import ingest_weekly_grants

router = APIRouter()

DEFAULT_THEMES = [
    {"name": "Human Necessities", "cpc_prefixes": ["A"], "assignee_keywords": [], "title_keywords": [], "description": "Biotechnology, pharma, food, agriculture"},
    {"name": "Performing Operations", "cpc_prefixes": ["B"], "assignee_keywords": [], "title_keywords": [], "description": "Manufacturing, transport, tools"},
    {"name": "Chemistry & Metallurgy", "cpc_prefixes": ["C"], "assignee_keywords": [], "title_keywords": [], "description": "Chemical processes, materials, metallurgy"},
    {"name": "Textiles & Paper", "cpc_prefixes": ["D"], "assignee_keywords": [], "title_keywords": [], "description": "Textiles, paper, flexible materials"},
    {"name": "Fixed Constructions", "cpc_prefixes": ["E"], "assignee_keywords": [], "title_keywords": [], "description": "Building, construction, mining"},
    {"name": "Mechanical Engineering", "cpc_prefixes": ["F"], "assignee_keywords": [], "title_keywords": [], "description": "Engines, pumps, mechanical systems"},
    {"name": "Physics & Computing", "cpc_prefixes": ["G"], "assignee_keywords": [], "title_keywords": [], "description": "AI/ML, computing, optics, instruments"},
    {"name": "Electricity & Electronics", "cpc_prefixes": ["H"], "assignee_keywords": [], "title_keywords": [], "description": "Electronics, communications, energy"},
]


class TriggerIngestRequest(BaseModel):
    type: Literal["grants", "applications", "epo", "pct"] = Field(...)
    target_date: date | None = None
    max_results: int | None = Field(default=None, ge=1, le=1000)


@router.post("/trigger-ingest", response_model=TaskStatusResponse)
async def trigger_ingest(request: TriggerIngestRequest) -> TaskStatusResponse:
    """
    Manually trigger patent ingestion (development only).

    Supported types:
    - grants: USPTO granted patents (Tuesday)
    - applications: USPTO published applications (Thursday)
    - epo: EPO publications (Wednesday) - requires EPO credentials
    - pct: WIPO PCT applications (Thursday)

    Enqueues the appropriate Celery task and returns the task ID.
    """
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production")

    target_date_str = request.target_date.isoformat() if request.target_date else None

    if request.type == "grants":
        task = ingest_weekly_grants.delay(target_date_str)
    elif request.type == "applications":
        task = ingest_weekly_applications.delay(target_date_str)
    elif request.type == "epo":
        from app.tasks.ingest_epo import ingest_weekly_epo

        if not settings.epo_ops_client_id:
            raise HTTPException(
                status_code=400, detail="EPO OPS credentials not configured"
            )
        task = ingest_weekly_epo.delay(target_date_str)
    elif request.type == "pct":
        from app.tasks.ingest_wipo import ingest_weekly_pct

        max_results = request.max_results or 100
        task = ingest_weekly_pct.delay(target_date_str, max_results)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown type: {request.type}")

    return TaskStatusResponse(
        task_id=task.id,
        status="PENDING",
        result=None,
    )


@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get status of a Celery task."""
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production")

    result = AsyncResult(task_id, app=celery_app)

    return TaskStatusResponse(
        task_id=task_id,
        status=result.status,
        result=result.result if result.ready() else None,
    )


@router.post("/trigger-summarize", response_model=TaskStatusResponse)
async def trigger_batch_summarize(limit: int = 10) -> TaskStatusResponse:
    """
    Manually trigger batch summarization (development only).
    """
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production")

    from app.tasks.summarize import batch_summarize_pending

    task = batch_summarize_pending.delay(limit)

    return TaskStatusResponse(
        task_id=task.id,
        status="PENDING",
        result=None,
    )


@router.post("/trigger-family-resolution", response_model=TaskStatusResponse)
async def trigger_family_resolution(limit: int = 100) -> TaskStatusResponse:
    """
    Manually trigger INPADOC family resolution (development only).

    Requires EPO OPS credentials.
    """
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production")

    if not settings.epo_ops_client_id:
        raise HTTPException(status_code=400, detail="EPO OPS credentials not configured")

    from app.tasks.ingest_epo import resolve_epo_families

    task = resolve_epo_families.delay(limit)

    return TaskStatusResponse(
        task_id=task.id,
        status="PENDING",
        result=None,
    )


@router.post("/trigger-expiry-backfill", response_model=TaskStatusResponse)
async def trigger_expiry_backfill(settings: AppSettings) -> TaskStatusResponse:
    """
    Trigger backfill of USPTO grants from 2006-2011 for expiry window population (development only).
    """
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production")

    from app.tasks.ingest_grants import ingest_expiry_window_grants

    task = ingest_expiry_window_grants.delay()

    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)


@router.post("/seed-themes")
async def seed_themes(db: DbSession, settings: AppSettings) -> dict[str, Any]:
    """
    Seed default CPC-section themes if they don't already exist (development only).
    """
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production")

    from app.core.theme_models import Theme

    created = 0
    skipped = 0

    for theme_data in DEFAULT_THEMES:
        name = theme_data["name"]
        result = await db.execute(select(Theme).where(Theme.name == name))
        existing = result.scalar_one_or_none()

        if existing:
            skipped += 1
        else:
            theme = Theme(
                name=name,
                description=theme_data["description"],
                cpc_prefixes=theme_data["cpc_prefixes"],
                assignee_keywords=theme_data["assignee_keywords"],
                title_keywords=theme_data["title_keywords"],
            )
            db.add(theme)
            created += 1

    await db.commit()

    return {"created": created, "skipped": skipped}


@router.post("/trigger-enrich-abstracts", response_model=TaskStatusResponse)
async def trigger_enrich_abstracts(
    batch_size: int = 200,
) -> TaskStatusResponse:
    """
    Fetch abstracts from EPO OPS for patents missing them (development only).

    This is the critical step to get high-quality AI summaries.
    EPO OPS rate limit: ~120 requests/min, so 200 patents takes ~2 minutes.
    """
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production")

    if not settings.epo_ops_client_id:
        raise HTTPException(status_code=400, detail="EPO OPS credentials not configured")

    from app.tasks.enrich_abstracts import enrich_batch

    task = enrich_batch.delay(batch_size)

    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)


@router.post("/trigger-resummarize", response_model=TaskStatusResponse)
async def trigger_resummarize(limit: int = 50) -> TaskStatusResponse:
    """
    Re-summarize patents that now have abstracts but were previously
    summarized with title-only (development only).
    """
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production")

    from app.tasks.summarize import batch_resummarize_enriched

    task = batch_resummarize_enriched.delay(limit)

    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)


@router.post("/trigger-match-themes", response_model=TaskStatusResponse)
async def trigger_match_themes(settings: AppSettings) -> TaskStatusResponse:
    """
    Trigger theme matching for all active themes (development only).
    """
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production")

    from app.tasks.theme_matcher import match_all_themes

    task = match_all_themes.delay(limit_per_theme=10000)

    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)
