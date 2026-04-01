from datetime import date
from typing import Literal

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.core.schemas import TaskStatusResponse
from app.tasks.celery_app import celery_app
from app.tasks.ingest_applications import ingest_weekly_applications
from app.tasks.ingest_grants import ingest_weekly_grants

router = APIRouter()


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
