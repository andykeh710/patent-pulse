import logging
from datetime import date
from datetime import datetime as _dt
from datetime import timezone as _tz
from typing import Any, Literal

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import AppSettings, DbSession, current_user, get_db
from app.config import settings
from app.core.ai_models import User as _UserModel
from app.core.schemas import TaskStatusResponse
from app.tasks.celery_app import celery_app
from app.tasks.ingest_applications import ingest_weekly_applications
from app.tasks.ingest_grants import ingest_weekly_grants

_log = logging.getLogger(__name__)

router = APIRouter()

DEFAULT_THEMES = [
    {
        "name": "Human Necessities",
        "cpc_prefixes": ["A"],
        "assignee_keywords": [],
        "title_keywords": [],
        "description": "Biotechnology, pharma, food, agriculture",
    },
    {
        "name": "Performing Operations",
        "cpc_prefixes": ["B"],
        "assignee_keywords": [],
        "title_keywords": [],
        "description": "Manufacturing, transport, tools",
    },
    {
        "name": "Chemistry & Metallurgy",
        "cpc_prefixes": ["C"],
        "assignee_keywords": [],
        "title_keywords": [],
        "description": "Chemical processes, materials, metallurgy",
    },
    {
        "name": "Textiles & Paper",
        "cpc_prefixes": ["D"],
        "assignee_keywords": [],
        "title_keywords": [],
        "description": "Textiles, paper, flexible materials",
    },
    {
        "name": "Fixed Constructions",
        "cpc_prefixes": ["E"],
        "assignee_keywords": [],
        "title_keywords": [],
        "description": "Building, construction, mining",
    },
    {
        "name": "Mechanical Engineering",
        "cpc_prefixes": ["F"],
        "assignee_keywords": [],
        "title_keywords": [],
        "description": "Engines, pumps, mechanical systems",
    },
    {
        "name": "Physics & Computing",
        "cpc_prefixes": ["G"],
        "assignee_keywords": [],
        "title_keywords": [],
        "description": "AI/ML, computing, optics, instruments",
    },
    {
        "name": "Electricity & Electronics",
        "cpc_prefixes": ["H"],
        "assignee_keywords": [],
        "title_keywords": [],
        "description": "Electronics, communications, energy",
    },
]

DEFAULT_TOPICS = [
    {
        "name": "AI Agents & LLMs",
        "description": "Autonomous agents, large language models, RAG, prompt engineering, multi-agent systems",
        "cpc_prefixes": ["G06N", "G06F"],
        "keywords": [
            "agent",
            "LLM",
            "large language model",
            "prompt",
            "retrieval augmented",
            "multi-agent",
            "autonomous",
            "reasoning",
        ],
        "opportunity_tags": ["startup", "enterprise", "cross_industry"],
        "min_opportunity_score": 30,
    },
    {
        "name": "Robotics & Automation",
        "description": "Industrial robots, autonomous vehicles, manipulation, perception, human-robot interaction",
        "cpc_prefixes": ["B25J", "G05D", "G05B"],
        "keywords": [
            "robot",
            "autonomous",
            "manipulation",
            "gripper",
            "end effector",
            "SLAM",
            "path planning",
            "human-robot",
        ],
        "opportunity_tags": ["enterprise", "revival"],
        "min_opportunity_score": 25,
    },
    {
        "name": "Climate Tech",
        "description": "Carbon capture, renewable energy, energy storage, green materials, climate adaptation",
        "cpc_prefixes": ["Y02E", "Y02C", "Y02P", "B01D"],
        "keywords": [
            "carbon capture",
            "renewable",
            "solar",
            "wind",
            "battery",
            "energy storage",
            "hydrogen",
            "decarbonization",
        ],
        "opportunity_tags": ["sustainability", "startup"],
        "min_opportunity_score": 25,
    },
    {
        "name": "Battery Technology",
        "description": "Lithium-ion, solid-state, sodium-ion, flow batteries, battery management systems",
        "cpc_prefixes": ["H01M", "H02J"],
        "keywords": [
            "lithium",
            "solid state",
            "sodium ion",
            "cathode",
            "anode",
            "electrolyte",
            "BMS",
            "thermal runaway",
        ],
        "opportunity_tags": ["enterprise", "sustainability"],
        "min_opportunity_score": 30,
    },
    {
        "name": "Biotech & Gene Therapy",
        "description": "CRISPR, mRNA, cell therapy, gene editing, protein engineering, precision medicine",
        "cpc_prefixes": ["C12N", "C07K", "A61K"],
        "keywords": [
            "CRISPR",
            "mRNA",
            "gene therapy",
            "cell therapy",
            "CAR-T",
            "protein engineering",
            "monoclonal antibody",
        ],
        "opportunity_tags": ["startup", "revival"],
        "min_opportunity_score": 30,
    },
    {
        "name": "Quantum Computing",
        "description": "Quantum processors, error correction, quantum algorithms, quantum networking, quantum sensing",
        "cpc_prefixes": ["G06N", "H01L"],
        "keywords": [
            "quantum",
            "qubit",
            "superconducting",
            "trapped ion",
            "quantum error",
            "quantum annealing",
            "entanglement",
        ],
        "opportunity_tags": ["cross_industry", "startup"],
        "min_opportunity_score": 25,
    },
]


class TriggerIngestRequest(BaseModel):
    type: Literal["grants", "applications", "epo", "pct"] = Field(...)
    target_date: date | None = None


async def require_admin(
    user_id: str = Depends(current_user),
    db=Depends(get_db),
) -> _UserModel:
    user = (
        await db.execute(select(_UserModel).where(_UserModel.id == user_id))
    ).scalar_one_or_none()
    if user is None or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    return user


@router.post("/trigger-ingest", response_model=TaskStatusResponse)
async def trigger_ingest(
    request: TriggerIngestRequest, _admin=Depends(require_admin)
) -> TaskStatusResponse:
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
            raise HTTPException(status_code=400, detail="EPO OPS credentials not configured")
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
async def trigger_batch_summarize(
    limit: int = 10, _admin=Depends(require_admin)
) -> TaskStatusResponse:
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
async def trigger_family_resolution(
    limit: int = 100, _admin=Depends(require_admin)
) -> TaskStatusResponse:
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
async def trigger_expiry_backfill(
    settings: AppSettings, _admin=Depends(require_admin)
) -> TaskStatusResponse:
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
    _admin=Depends(require_admin),
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
async def trigger_resummarize(limit: int = 50, _admin=Depends(require_admin)) -> TaskStatusResponse:
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
async def trigger_match_themes(
    settings: AppSettings, _admin=Depends(require_admin)
) -> TaskStatusResponse:
    """
    Trigger theme matching for all active themes (development only).
    """
    if settings.environment == "production":
        raise HTTPException(status_code=403, detail="Not available in production")

    from app.tasks.theme_matcher import match_all_themes

    task = match_all_themes.delay(limit_per_theme=10000)

    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)


# ── Sprint 7: Admin user management ──────────────────────────────────


class TierOverrideBody(BaseModel):
    tier: str
    reason: str | None = None


@router.get("/users")
async def admin_list_users(
    admin: _UserModel = Depends(require_admin),
    db=Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    from app.core.ai_models import User
    from app.core.billing_models import BillingSubscription

    total = (await db.execute(select(func.count()).select_from(User))).scalar()
    users = (
        (
            await db.execute(
                select(User)
                .offset((page - 1) * page_size)
                .limit(page_size)
                .order_by(User.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    user_ids = [u.id for u in users]
    billing_map = {}
    if user_ids:
        rows = (
            (
                await db.execute(
                    select(BillingSubscription).where(BillingSubscription.user_id.in_(user_ids))
                )
            )
            .scalars()
            .all()
        )
        billing_map = {b.user_id: b for b in rows}
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "display_name": u.display_name,
                "tier": u.tier,
                "billing_status": billing_map[u.id].status if u.id in billing_map else None,
                "current_period_end": billing_map[u.id].current_period_end.isoformat()
                if u.id in billing_map and billing_map[u.id].current_period_end
                else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
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
    existing = (
        await db.execute(select(BillingSubscription).where(BillingSubscription.user_id == user_id))
    ).scalar_one_or_none()
    row = existing or BillingSubscription(user_id=user_id)
    row.tier = body.tier
    row.status = "active"
    row.updated_at = _dt.now(_tz.utc)
    db.add(row)
    await db.commit()
    _log.info(
        "Admin tier override: user=%s old=%s new=%s reason=%s",
        user_id,
        old_tier,
        body.tier,
        body.reason,
    )
    return {"user_id": user_id, "tier": body.tier, "old_tier": old_tier}


@router.get("/exports")
async def admin_list_exports(admin: _UserModel = Depends(require_admin), db=Depends(get_db)):
    from app.core.ai_models import User
    from app.core.billing_models import Export

    exports = (
        (await db.execute(select(Export).order_by(Export.created_at.desc()).limit(100)))
        .scalars()
        .all()
    )
    user_ids = list({e.user_id for e in exports})
    users_map = {}
    if user_ids:
        users_map = {
            u.id: u.email or u.id
            for u in (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        }
    return [
        {
            "id": str(e.id),
            "user_id": e.user_id,
            "user_email": users_map.get(e.user_id, e.user_id),
            "export_type": e.export_type,
            "scope": e.scope,
            "payload_size_bytes": e.payload_size_bytes,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in exports
    ]


@router.post("/debug/sentry")
async def trigger_sentry_test(
    admin: _UserModel = Depends(require_admin),
):
    """Trigger a test exception to verify the Sentry pipeline.

    Returns 500 with a unique marker so the admin can identify the
    corresponding event in Sentry.
    """
    raise RuntimeError("PR8 Sentry debug — intentional test exception")


# ── System health ────────────────────────────────────────────


@router.get("/system-health")
async def admin_system_health(
    admin: _UserModel = Depends(require_admin),
):
    """Returns Anthropic API health status for monitoring."""
    from app.tasks.tag import (
        _LAST_ANTHROPIC_ERROR_AT,
        ANTHROPIC_ERROR_MAX_CONSECUTIVE,
        _anthropic_error_count,
    )

    status = "ok"
    if _anthropic_error_count >= ANTHROPIC_ERROR_MAX_CONSECUTIVE:
        status = "credits_exhausted"
    elif _anthropic_error_count > 0:
        status = "degraded"

    return {
        "anthropic_status": status,
        "anthropic_consecutive_errors": _anthropic_error_count,
        "anthropic_last_error_at": _LAST_ANTHROPIC_ERROR_AT,
        "circuit_broken": _anthropic_error_count >= ANTHROPIC_ERROR_MAX_CONSECUTIVE,
    }


# ── Data health ──────────────────────────────────────────────


@router.get("/llm-provider")
async def admin_llm_provider(
    admin: _UserModel = Depends(require_admin),
):
    """Check current LLM provider."""
    return {
        "provider": settings.llm_provider or "deepseek",
        "model": settings.deepseek_chat_model
        if (settings.llm_provider or "deepseek") == "deepseek"
        else settings.claude_model,
        "deepseek_configured": bool(settings.deepseek_api_key),
        "anthropic_configured": bool(settings.anthropic_api_key),
    }


@router.post("/llm-provider")
async def admin_set_llm_provider(
    payload: dict[str, str],
    admin: _UserModel = Depends(require_admin),
):
    """Switch LLM provider. Writes to a runtime override. Requires restart."""
    provider = (payload.get("provider") or "").lower()
    if provider not in ("deepseek", "anthropic"):
        raise HTTPException(400, "provider must be 'deepseek' or 'anthropic'")
    # Write to app.env for persistence across restarts
    import os

    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "app.env")
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "app.env"))
    try:
        with open(env_path, "r") as f:
            lines = f.readlines()
        with open(env_path, "w") as f:
            found = False
            for line in lines:
                if line.startswith("LLM_PROVIDER="):
                    f.write(f"LLM_PROVIDER={provider}\n")
                    found = True
                else:
                    f.write(line)
            if not found:
                f.write(f"\nLLM_PROVIDER={provider}\n")
        # Update runtime setting
        settings.llm_provider = provider
        return {"provider": provider, "restart_required": True}
    except Exception as e:
        raise HTTPException(500, f"Failed to update: {e}")


@router.get("/data-health")
async def admin_data_health(
    admin: _UserModel = Depends(require_admin),
    db=Depends(get_db),
):
    """Aggregated patent data health across offices and coverage axes."""
    from app.core.models import PatentPublication, SourceFetch

    # Per-office counts
    office_rows = (
        await db.execute(
            select(
                PatentPublication.office,
                func.count(PatentPublication.id).label("total"),
                func.count(PatentPublication.abstract).label("with_abstract"),
                func.count(PatentPublication.claims_text).label("with_claims"),
                func.count(PatentPublication.figure_page_url).label("with_figure_url"),
                func.count(PatentPublication.embedding).label("with_embedding"),
                func.count(PatentPublication.tags).label("with_tags"),
                func.count(PatentPublication.summarized_at).label("with_summary"),
            ).group_by(PatentPublication.office)
        )
    ).all()

    # Citation coverage
    citation_stats = (
        await db.execute(
            select(
                func.count(PatentPublication.id).label("total_patents"),
                func.count(PatentPublication.id)
                .filter(func.jsonb_array_length(PatentPublication.citations_forward) > 0)
                .label("with_forward_citations"),
                func.count(PatentPublication.id)
                .filter(func.jsonb_array_length(PatentPublication.citations_backward) > 0)
                .label("with_backward_citations"),
            )
        )
    ).one()

    # Family coverage
    family_stats = (
        await db.execute(
            select(
                func.count(PatentPublication.id)
                .filter(PatentPublication.family_id.isnot(None))
                .label("with_family_id"),
                func.count(PatentPublication.id)
                .filter(func.jsonb_array_length(PatentPublication.family_members) > 0)
                .label("with_family_members"),
            )
        )
    ).one()

    # Recent source_fetches failures
    recent_failures = (
        (
            await db.execute(
                select(SourceFetch)
                .where(SourceFetch.status.in_(["failed", "blocked"]))
                .order_by(SourceFetch.created_at.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )

    # Latest success per provider
    latest_success = (
        await db.execute(
            select(
                SourceFetch.provider,
                func.max(SourceFetch.created_at).label("last_success"),
            )
            .where(SourceFetch.status == "success")
            .group_by(SourceFetch.provider)
        )
    ).all()

    total = sum(r.total for r in office_rows)

    return {
        "total_patents": total,
        "by_office": [
            {
                "office": r.office,
                "total": r.total,
                "abstract_pct": round(r.with_abstract / r.total * 100, 1) if r.total else 0,
                "claims_pct": round(r.with_claims / r.total * 100, 1) if r.total else 0,
                "figure_url_pct": round(r.with_figure_url / r.total * 100, 1) if r.total else 0,
                "embedding_pct": round(r.with_embedding / r.total * 100, 1) if r.total else 0,
                "tags_pct": round(r.with_tags / r.total * 100, 1) if r.total else 0,
                "summary_pct": round(r.with_summary / r.total * 100, 1) if r.total else 0,
            }
            for r in office_rows
        ],
        "citations": {
            "total": citation_stats.total_patents,
            "forward_pct": round(
                citation_stats.with_forward_citations / citation_stats.total_patents * 100, 1
            )
            if citation_stats.total_patents
            else 0,
            "backward_pct": round(
                citation_stats.with_backward_citations / citation_stats.total_patents * 100, 1
            )
            if citation_stats.total_patents
            else 0,
        },
        "family": {
            "with_family_id": family_stats.with_family_id,
            "with_family_members": family_stats.with_family_members,
        },
        "recent_failures": [
            {
                "id": str(f.id),
                "provider": f.provider,
                "target_type": f.target_type,
                "target_id": f.target_id,
                "error_message": f.error_message[:200] if f.error_message else None,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in recent_failures
        ],
        "latest_success_by_provider": {
            r.provider: r.last_success.isoformat() if r.last_success else None
            for r in latest_success
        },
    }


@router.get("/source-fetches")
async def admin_source_fetches(
    admin: _UserModel = Depends(require_admin),
    db=Depends(get_db),
    limit: int = 20,
    provider: str | None = None,
    status: str | None = None,
):
    """Recent source fetch log entries."""
    from app.core.models import SourceFetch

    q = select(SourceFetch).order_by(SourceFetch.created_at.desc())
    if provider:
        q = q.where(SourceFetch.provider == provider)
    if status:
        q = q.where(SourceFetch.status == status)
    q = q.limit(min(limit, 100))

    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(r.id),
            "provider": r.provider,
            "office": r.office,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "source_url": r.source_url,
            "status": r.status,
            "http_status": r.http_status,
            "error_message": r.error_message[:300] if r.error_message else None,
            "records_found": r.records_found,
            "duration_ms": r.duration_ms,
            "retry_count": r.retry_count,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ── Phase 1: Admin embedding management ──────────────────────────


@router.post("/embed/{patent_id}")
async def admin_re_embed_patent(
    patent_id: str,
    admin: _UserModel = Depends(require_admin),
    db=Depends(get_db),
):
    """Force (re-)generate the embedding for a single patent.

    Overwrites any existing embedding. Requires admin access.
    """
    from uuid import UUID

    from app.ai.embedder import EmbeddingError, PatentEmbedder
    from app.core.models import PatentPublication

    try:
        pid = UUID(patent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patent ID format")

    result = await db.execute(select(PatentPublication).where(PatentPublication.id == pid))
    patent = result.scalar_one_or_none()

    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")

    if not patent.title and not patent.abstract:
        raise HTTPException(
            status_code=400,
            detail="Patent has no title or abstract — nothing to embed",
        )

    try:
        with PatentEmbedder() as embedder:
            embedding = embedder.generate_patent_embedding(patent)
    except EmbeddingError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Embedding generation failed: {e}",
        )

    patent.embedding = embedding
    await db.commit()

    return {
        "patent_id": str(patent.id),
        "doc_id": patent.doc_id,
        "status": "re-embedded",
        "dimensions": len(embedding),
    }


@router.get("/embedding-stats")
async def admin_embedding_stats(
    admin: _UserModel = Depends(require_admin),
    db=Depends(get_db),
):
    """Return embedding coverage statistics.

    Requires admin access.
    """
    from app.core.models import PatentPublication

    row = (
        await db.execute(
            select(
                func.count(PatentPublication.id).label("total"),
                func.count(PatentPublication.id)
                .filter(PatentPublication.embedding.isnot(None))
                .label("embedded"),
            )
        )
    ).one()

    total = row.total or 0
    embedded = row.embedded or 0
    coverage_pct = round(embedded / total * 100, 1) if total > 0 else 0.0

    return {
        "total_patents": total,
        "embedded": embedded,
        "missing": total - embedded,
        "coverage_pct": coverage_pct,
    }


# ── Phase 4 PR 1: Billing health ──────────────────────────────


@router.get("/billing/health")
async def admin_billing_health(
    admin: _UserModel = Depends(require_admin),
    db=Depends(get_db),
):
    """Admin-only billing health endpoint — reports Stripe mode and stats.

    Returns mode, active subscription count, webhook secret status,
    and does NOT leak secret material.
    """
    from datetime import datetime, timedelta, timezone

    from app.core.billing_models import BillingSubscription

    # Active subscription count
    active_count = (
        await db.execute(
            select(func.count(BillingSubscription.id)).where(BillingSubscription.status == "active")
        )
    ).scalar() or 0

    # Recent webhook events (last 24h summary — count per type)
    # We don't have a webhook events table, but we can count recent
    # BillingSubscription updates as a proxy for webhook activity.
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_activity = (
        await db.execute(
            select(func.count(BillingSubscription.id)).where(
                BillingSubscription.updated_at >= since
            )
        )
    ).scalar() or 0

    # Tier breakdown
    free_count = (
        await db.execute(
            select(func.count(BillingSubscription.id)).where(BillingSubscription.tier == "free")
        )
    ).scalar() or 0
    basic_count = (
        await db.execute(
            select(func.count(BillingSubscription.id)).where(BillingSubscription.tier == "basic")
        )
    ).scalar() or 0
    lifetime_count = (
        await db.execute(
            select(func.count(BillingSubscription.id)).where(BillingSubscription.tier == "lifetime")
        )
    ).scalar() or 0
    enterprise_count = (
        await db.execute(
            select(func.count(BillingSubscription.id)).where(
                BillingSubscription.tier == "enterprise"
            )
        )
    ).scalar() or 0

    return {
        "mode": settings.stripe_mode,
        "test_key_in_use": bool(
            settings.stripe_api_key and settings.stripe_api_key.startswith("sk_test_")
        ),
        "live_key_in_use": bool(
            settings.stripe_api_key and settings.stripe_api_key.startswith("sk_live_")
        ),
        "webhook_secret_set": bool(settings.stripe_webhook_secret),
        "subscriptions": {
            "active": active_count,
            "free": free_count,
            "basic": basic_count,
            "lifetime": lifetime_count,
            "enterprise": enterprise_count,
        },
        "recent_webhook_activity_24h": recent_activity,
        "stripe_api_key_configured": bool(settings.stripe_api_key),
    }


# ── Phase 5 PR 1: Email analytics ─────────────────────────────


@router.get("/email/analytics")
async def admin_email_analytics(
    admin: _UserModel = Depends(require_admin),
    db=Depends(get_db),
):
    """Admin-only email analytics — open/click rates + A/B variant breakdown.

    Returns aggregate stats for last 7 days and per-subject-variant.
    """
    from datetime import datetime, timedelta, timezone

    from app.core.subscription_models import EmailDelivery

    since = datetime.now(timezone.utc) - timedelta(days=7)

    # ── Global stats ──────────────────────────────────────────────
    sent = (
        await db.execute(
            select(func.count(EmailDelivery.id)).where(
                EmailDelivery.email_type == "weekly_briefing",
                EmailDelivery.sent_at >= since,
            )
        )
    ).scalar() or 0

    opens = (
        await db.execute(
            select(func.count(EmailDelivery.id)).where(
                EmailDelivery.email_type == "weekly_briefing",
                EmailDelivery.sent_at >= since,
                EmailDelivery.email_opened_at.isnot(None),
            )
        )
    ).scalar() or 0

    clicks = (
        await db.execute(
            select(func.count(EmailDelivery.id)).where(
                EmailDelivery.email_type == "weekly_briefing",
                EmailDelivery.sent_at >= since,
                EmailDelivery.email_clicked_at.isnot(None),
            )
        )
    ).scalar() or 0

    open_rate = round(opens / sent, 3) if sent > 0 else 0.0
    click_rate = round(clicks / sent, 3) if sent > 0 else 0.0

    # ── Per-variant breakdown ─────────────────────────────────────
    variant_rows = (
        await db.execute(
            select(
                EmailDelivery.subject_variant,
                func.count(EmailDelivery.id).label("total"),
                func.count(EmailDelivery.id)
                .filter(EmailDelivery.email_opened_at.isnot(None))
                .label("opens"),
            )
            .where(
                EmailDelivery.email_type == "weekly_briefing",
                EmailDelivery.sent_at >= since,
                EmailDelivery.subject_variant.isnot(None),
            )
            .group_by(EmailDelivery.subject_variant)
        )
    ).all()

    by_variant = {}
    for row in variant_rows:
        v_sent = row.total or 0
        v_opens = row.opens or 0
        by_variant[str(row.subject_variant)] = {
            "sent": v_sent,
            "opens": v_opens,
            "open_rate": round(v_opens / v_sent, 3) if v_sent > 0 else 0.0,
        }

    return {
        "last_7_days": {
            "sent": sent,
            "opens": opens,
            "open_rate": open_rate,
            "clicks": clicks,
            "click_rate": click_rate,
        },
        "by_variant": by_variant,
    }


# ── V3.5: Source Health & Ingestion Admin ────────────────────────


class RetryGrantWeekBody(BaseModel):
    issue_date: str  # YYYY-MM-DD


class RetryAppWeekBody(BaseModel):
    publication_date: str  # YYYY-MM-DD


class CatchUpBody(BaseModel):
    start_date: str  # YYYY-MM-DD
    end_date: str | None = None  # YYYY-MM-DD, defaults to today


@router.get("/source-health")
async def admin_source_health(
    admin: _UserModel = Depends(require_admin),
    db=Depends(get_db),
):
    """Aggregated source health — ingestion providers, latest status, source lag."""
    from app.core.models import PatentPublication, SourceFetch

    freshness_row = (
        await db.execute(
            select(
                func.count(PatentPublication.id).label("total"),
                func.max(PatentPublication.publication_date).label("latest_pub_date"),
                func.max(PatentPublication.created_at).label("latest_ingested_at"),
            )
        )
    ).one()

    providers = ["uspto_bulkdata", "uspto_odp", "bigquery", "wipo_bigquery"]
    provider_rows = []
    for provider in providers:
        latest = (
            await db.execute(
                select(SourceFetch)
                .where(SourceFetch.provider == provider)
                .order_by(SourceFetch.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        latest_success = (
            await db.execute(
                select(SourceFetch)
                .where(SourceFetch.provider == provider, SourceFetch.status == "success")
                .order_by(SourceFetch.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        latest_failure = (
            await db.execute(
                select(SourceFetch)
                .where(
                    SourceFetch.provider == provider,
                    SourceFetch.status.in_(["failed", "blocked", "unavailable"]),
                )
                .order_by(SourceFetch.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if latest or latest_success or latest_failure:
            provider_rows.append(
                {
                    "provider": provider,
                    "latest_status": latest.status if latest else "unknown",
                    "latest_target_type": latest.target_type if latest else None,
                    "latest_target_id": latest.target_id if latest else None,
                    "latest_http_status": latest.http_status if latest else None,
                    "latest_records_found": latest.records_found if latest else None,
                    "latest_error": (
                        latest.error_message[:200] if latest and latest.error_message else None
                    ),
                    "latest_started_at": latest.started_at.isoformat()
                    if latest and latest.started_at
                    else None,
                    "latest_success_at": latest_success.created_at.isoformat()
                    if latest_success and latest_success.created_at
                    else None,
                    "latest_failure_at": latest_failure.created_at.isoformat()
                    if latest_failure and latest_failure.created_at
                    else None,
                    "latest_source_url": latest.source_url if latest else None,
                }
            )

    source_lag_days = None
    if freshness_row.latest_pub_date:
        source_lag_days = (date.today() - freshness_row.latest_pub_date).days

    return {
        "total_patents": freshness_row.total,
        "latest_publication_date": freshness_row.latest_pub_date.isoformat()
        if freshness_row.latest_pub_date
        else None,
        "latest_ingested_at": freshness_row.latest_ingested_at.isoformat()
        if freshness_row.latest_ingested_at
        else None,
        "source_lag_days": source_lag_days,
        "providers": provider_rows,
    }


@router.post("/ingestion/retry-grant-week", response_model=TaskStatusResponse)
async def retry_grant_week(
    body: RetryGrantWeekBody,
    admin: _UserModel = Depends(require_admin),
) -> TaskStatusResponse:
    """Retry USPTO grant week ingestion for a specific Tuesday issue date."""
    from app.tasks.ingest_uspto_bulk import ingest_grant_week

    task = ingest_grant_week.delay(body.issue_date)
    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)


@router.post("/ingestion/retry-application-week", response_model=TaskStatusResponse)
async def retry_application_week(
    body: RetryAppWeekBody,
    admin: _UserModel = Depends(require_admin),
) -> TaskStatusResponse:
    """Retry USPTO application week ingestion for a specific Thursday publication date."""
    from app.tasks.ingest_uspto_bulk import ingest_application_week

    task = ingest_application_week.delay(body.publication_date)
    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)


@router.post("/ingestion/catch-up", response_model=TaskStatusResponse)
async def catch_up(
    body: CatchUpBody,
    admin: _UserModel = Depends(require_admin),
) -> TaskStatusResponse:
    """Run catch-up ingestion across a date range (grant + application weeks)."""
    from app.tasks.ingest_uspto_bulk import catch_up_weeks

    task = catch_up_weeks.delay(body.start_date, body.end_date)
    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)
