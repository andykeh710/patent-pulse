from datetime import date
from typing import Any, Literal

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func

from app.api.deps import AppSettings, DbSession, get_db, current_user
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

DEFAULT_TOPICS = [
    {
        "name": "AI Agents & LLMs",
        "description": "Autonomous agents, large language models, RAG, prompt engineering, multi-agent systems",
        "cpc_prefixes": ["G06N", "G06F"],
        "keywords": ["agent", "LLM", "large language model", "prompt", "retrieval augmented", "multi-agent", "autonomous", "reasoning"],
        "opportunity_tags": ["startup", "enterprise", "cross_industry"],
        "min_opportunity_score": 30,
    },
    {
        "name": "Robotics & Automation",
        "description": "Industrial robots, autonomous vehicles, manipulation, perception, human-robot interaction",
        "cpc_prefixes": ["B25J", "G05D", "G05B"],
        "keywords": ["robot", "autonomous", "manipulation", "gripper", "end effector", "SLAM", "path planning", "human-robot"],
        "opportunity_tags": ["enterprise", "revival"],
        "min_opportunity_score": 25,
    },
    {
        "name": "Climate Tech",
        "description": "Carbon capture, renewable energy, energy storage, green materials, climate adaptation",
        "cpc_prefixes": ["Y02E", "Y02C", "Y02P", "B01D"],
        "keywords": ["carbon capture", "renewable", "solar", "wind", "battery", "energy storage", "hydrogen", "decarbonization"],
        "opportunity_tags": ["sustainability", "startup"],
        "min_opportunity_score": 25,
    },
    {
        "name": "Battery Technology",
        "description": "Lithium-ion, solid-state, sodium-ion, flow batteries, battery management systems",
        "cpc_prefixes": ["H01M", "H02J"],
        "keywords": ["lithium", "solid state", "sodium ion", "cathode", "anode", "electrolyte", "BMS", "thermal runaway"],
        "opportunity_tags": ["enterprise", "sustainability"],
        "min_opportunity_score": 30,
    },
    {
        "name": "Biotech & Gene Therapy",
        "description": "CRISPR, mRNA, cell therapy, gene editing, protein engineering, precision medicine",
        "cpc_prefixes": ["C12N", "C07K", "A61K"],
        "keywords": ["CRISPR", "mRNA", "gene therapy", "cell therapy", "CAR-T", "protein engineering", "monoclonal antibody"],
        "opportunity_tags": ["startup", "revival"],
        "min_opportunity_score": 30,
    },
    {
        "name": "Quantum Computing",
        "description": "Quantum processors, error correction, quantum algorithms, quantum networking, quantum sensing",
        "cpc_prefixes": ["G06N", "H01L"],
        "keywords": ["quantum", "qubit", "superconducting", "trapped ion", "quantum error", "quantum annealing", "entanglement"],
        "opportunity_tags": ["cross_industry", "startup"],
        "min_opportunity_score": 25,
    },
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
    Seed default CPC-section themes and user topic packs if they don't already exist
    (development only).
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

    # Seed default user topic packs
    for topic_data in DEFAULT_TOPICS:
        name = topic_data["name"]
        result = await db.execute(select(Theme).where(Theme.name == name))
        existing = result.scalar_one_or_none()

        if existing:
            skipped += 1
        else:
            theme = Theme(
                name=name,
                description=topic_data["description"],
                cpc_prefixes=topic_data["cpc_prefixes"],
                keywords=topic_data.get("keywords"),
                opportunity_tags=topic_data.get("opportunity_tags"),
                min_opportunity_score=topic_data.get("min_opportunity_score"),
                user_id="default_pack",
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


# ── Sprint 7: Admin user management ──────────────────────────────────

import logging
from datetime import datetime as _dt, timezone as _tz
_log = logging.getLogger(__name__)


class TierOverrideBody(BaseModel):
    tier: str
    reason: str | None = None


from app.core.ai_models import User as _UserModel

async def require_admin(
    user_id: str = Depends(current_user),
    db = Depends(get_db),
) -> _UserModel:
    user = (await db.execute(select(_UserModel).where(_UserModel.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    return user


@router.get("/users")
async def admin_list_users(
    admin: _UserModel = Depends(require_admin),
    db = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    from app.core.ai_models import User
    from app.core.billing_models import BillingSubscription
    total = (await db.execute(
        select(func.count()).select_from(User)
    )).scalar()
    users = (await db.execute(
        select(User).offset((page - 1) * page_size).limit(page_size).order_by(User.created_at.desc())
    )).scalars().all()
    user_ids = [u.id for u in users]
    billing_map = {}
    if user_ids:
        rows = (await db.execute(
            select(BillingSubscription).where(BillingSubscription.user_id.in_(user_ids))
        )).scalars().all()
        billing_map = {b.user_id: b for b in rows}
    return {
        "users": [{
            "id": u.id, "email": u.email, "display_name": u.display_name,
            "tier": u.tier,
            "billing_status": billing_map[u.id].status if u.id in billing_map else None,
            "current_period_end": billing_map[u.id].current_period_end.isoformat() if u.id in billing_map and billing_map[u.id].current_period_end else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        } for u in users],
        "total": total, "page": page,
    }


@router.post("/users/{user_id}/tier")
async def admin_override_tier(
    user_id: str,
    body: TierOverrideBody,
    admin: _UserModel = Depends(require_admin),
    db=Depends(get_db),
):
    from app.core.ai_models import User
    from app.core.billing_models import BillingSubscription
    if body.tier not in ("free", "basic", "lifetime", "enterprise"):
        raise HTTPException(status_code=422, detail=f"Invalid tier: {body.tier}")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    old_tier = user.tier
    user.tier = body.tier
    await db.commit()
    existing = (await db.execute(
        select(BillingSubscription).where(BillingSubscription.user_id == user_id)
    )).scalar_one_or_none()
    row = existing or BillingSubscription(user_id=user_id)
    row.tier = body.tier
    row.status = "active"
    row.updated_at = _dt.now(_tz.utc)
    db.add(row)
    await db.commit()
    _log.info("Admin tier override: user=%s old=%s new=%s reason=%s", user_id, old_tier, body.tier, body.reason)
    return {"user_id": user_id, "tier": body.tier, "old_tier": old_tier}


@router.get("/exports")
async def admin_list_exports(admin: _UserModel = Depends(require_admin), db=Depends(get_db)):
    from app.core.ai_models import User
    from app.core.billing_models import Export
    exports = (await db.execute(
        select(Export).order_by(Export.created_at.desc()).limit(100)
    )).scalars().all()
    user_ids = list({e.user_id for e in exports})
    users_map = {}
    if user_ids:
        users_map = {u.id: u.email or u.id for u in (
            await db.execute(select(User).where(User.id.in_(user_ids)))
        ).scalars().all()}
    return [{
        "id": str(e.id), "user_id": e.user_id,
        "user_email": users_map.get(e.user_id, e.user_id),
        "export_type": e.export_type, "scope": e.scope,
        "payload_size_bytes": e.payload_size_bytes,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    } for e in exports]


@router.post("/debug/sentry")
async def trigger_sentry_test(
    admin: _UserModel = Depends(require_admin),
):
    """Trigger a test exception to verify the Sentry pipeline.

    Returns 500 with a unique marker so the admin can identify the
    corresponding event in Sentry.
    """
    raise RuntimeError("PR8 Sentry debug — intentional test exception")
