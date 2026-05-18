"""
Admin AI Runs API.

Powers the ``/admin/ai-runs`` console:

* ``POST /ai-runs/estimate``  — cost-preview for a task + cohort without
  touching the LLM provider. Inspects the AIArtifact cache to report
  ``cached_count`` vs ``uncached_count``.
* ``POST /ai-runs``           — create (and optionally enqueue) a run.
* ``GET  /ai-runs``           — run-history list.
* ``GET  /ai-runs/{id}``      — run detail + linked artifacts summary.

Task types implemented today:
  Phase 0: ``summary`` (LLM, Sonnet)
  Phase 1: ``tags`` (LLM, Haiku) and ``opportunity_score`` (rules, $0)
Other types still return 501 until the respective Phase 2-4 modules land.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select

from app.ai.assignee_intelligence import (
    DEFAULT_WEIGHTS as ASSIGNEE_WEIGHTS,
    RULES_ID as ASSIGNEE_RULES_ID,
    RULES_VERSION as ASSIGNEE_RULES_VERSION,
)
from app.ai.llm_client import (
    _model_for_tier,
    estimate_cost_usd,
    estimate_tokens,
    hash_rules,
)
from app.ai.opportunity_narrative import (
    OPPORTUNITY_NARRATIVE_PROMPT_NAME,
    OPPORTUNITY_NARRATIVE_PROMPT_VERSION,
    build_payload as build_opportunity_narrative_payload,
)
from app.ai.opportunity_scorer import (
    DEFAULT_WEIGHTS as OPPORTUNITY_WEIGHTS,
    RULES_ID as OPPORTUNITY_RULES_ID,
    RULES_VERSION as OPPORTUNITY_RULES_VERSION,
)
from app.ai.prompts import get_prompt
from app.ai.summarizer import (
    SUMMARY_PROMPT_NAME,
    SUMMARY_PROMPT_VERSION,
    build_summary_payload,
)
from app.ai.tagger import (
    TAG_PROMPT_NAME,
    TAG_PROMPT_VERSION,
    build_tag_payload,
)
from app.ai.trend_snapshot import (
    DEFAULT_WEIGHTS as TREND_WEIGHTS,
    RULES_ID as TREND_RULES_ID,
    RULES_VERSION as TREND_RULES_VERSION,
)
from app.ai.why_now import (
    WHY_NOW_PROMPT_NAME,
    WHY_NOW_PROMPT_VERSION,
    build_payload as build_why_now_payload,
)
from app.api.deps import AppSettings, DbSession
from app.core.ai_models import (
    ARTIFACT_TYPES,
    RUN_MODES,
    AIArtifact,
    AIRun,
)
from app.core.models import PatentPublication

router = APIRouter()
logger = logging.getLogger(__name__)
FULL_BATCH_CONFIRMATION_PHRASE = "RUN FULL BATCH"

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class CohortFilter(BaseModel):
    """Subset of ``PatentPublication`` filters; mirrored by frontend."""

    patent_ids: list[UUID] | None = None
    cpc_prefix: str | None = None
    grant_year_from: int | None = None
    grant_year_to: int | None = None
    expiry_within_days: int | None = None
    has_summary: bool | None = None  # None=no filter, True=only summarized, False=only unsummarized
    has_abstract: bool | None = None
    has_tags: bool | None = None  # None=no filter, True=already tagged, False=needs tagging
    has_opportunity_score: bool | None = None
    min_interesting_score: float | None = None
    max_interesting_score: float | None = None
    limit: int | None = Field(default=None, ge=1, le=100_000)


# Task types the estimator can price today. Add Phase 2-4 types as the
# respective modules land.
ESTIMATABLE_TASK_TYPES = {"summary", "tags", "opportunity_score", "why_now", "opportunity_narrative", "trend_snapshot", "assignee_intelligence"}
# Subset that produces $0 rules-based artifacts.
RULES_TASK_TYPES = {"opportunity_score", "trend_snapshot", "assignee_intelligence"}


_TaskType = Literal[
    "summary",
    "tags",
    "why_now",
    "opportunity_narrative",
    "trend_narrative",
    "assignee_narrative",
    "score_rerank",
    "interesting_score",
    "opportunity_score",
]


class EstimateRequest(BaseModel):
    task_type: str
    run_mode: Literal["dev_fixture", "sample", "cohort", "full_batch"]
    cohort: CohortFilter = Field(default_factory=CohortFilter)
    tier: Literal["summary", "tag", "narrative", "rerank"] = "summary"


class EstimateResponse(BaseModel):
    task_type: str
    run_mode: str
    cohort_size: int
    cached_count: int
    uncached_count: int
    est_input_tokens: int
    est_output_tokens: int
    est_cost_usd: float
    model: str
    prompt_name: str
    prompt_version: int
    prompt_hash: str
    expected_cache_hit_rate_7d: float
    auto_approve_threshold_usd: float
    full_batch_threshold_usd: float
    requires_confirmation: bool
    requires_full_batch_phrase: bool


class CreateRunRequest(BaseModel):
    task_type: str
    run_mode: Literal["dev_fixture", "sample", "cohort", "full_batch"]
    cohort: CohortFilter = Field(default_factory=CohortFilter)
    confirmation_phrase: str | None = None  # required when run_mode=full_batch
    enqueue: bool = True  # if False, create the run row but do not kick off Celery
    tier: Literal["summary", "tag", "narrative", "rerank"] = "summary"


class RunSummary(BaseModel):
    id: UUID
    task_type: str
    run_mode: str
    status: str
    cohort_size: int
    cached_count: int
    uncached_count: int
    est_cost_usd: float
    actual_cost_usd: float
    completed_count: int
    failed_count: int
    model: str
    prompt_name: str | None
    prompt_version: int | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RunListResponse(BaseModel):
    items: list[RunSummary]
    total: int


# ---------------------------------------------------------------------------
# Cohort resolution
# ---------------------------------------------------------------------------


DEV_FIXTURE_SIZE = 50
SAMPLE_SIZE = 100


async def _resolve_cohort(
    db,
    *,
    run_mode: str,
    cohort: CohortFilter,
    task_type: str,
) -> list[UUID]:
    """Return the list of PatentPublication IDs that the run will process.

    Resolution rules:
     - ``dev_fixture``: first 50 patents by id (deterministic) that pass
       ``has_abstract=True`` so summarization has content.
     - ``sample``: first 100 patents sorted by grant_date desc.
     - ``cohort``: apply all filters; optionally honor ``cohort.limit``.
     - ``full_batch``: apply filters; no limit.
    """
    stmt = select(PatentPublication.id).order_by(PatentPublication.id)

    # dev_fixture + sample are opinionated, preset filters
    if run_mode == "dev_fixture":
        stmt = stmt.where(PatentPublication.abstract.isnot(None)).limit(
            DEV_FIXTURE_SIZE
        )
    elif run_mode == "sample":
        stmt = (
            select(PatentPublication.id)
            .order_by(PatentPublication.grant_date.desc().nullslast())
            .limit(SAMPLE_SIZE)
        )
    else:
        # Explicit patent ids short-circuit all other filters.
        if cohort.patent_ids:
            stmt = select(PatentPublication.id).where(
                PatentPublication.id.in_(cohort.patent_ids)
            )
        else:
            conditions = []
            if cohort.cpc_prefix:
                # Match any CPC prefix in the JSONB array.
                conditions.append(
                    func.jsonb_path_exists(
                        PatentPublication.cpc,
                        f'$[*] ? (@ starts with "{cohort.cpc_prefix}")',
                    )
                )
            if cohort.grant_year_from:
                conditions.append(
                    func.extract("year", PatentPublication.grant_date)
                    >= cohort.grant_year_from
                )
            if cohort.grant_year_to:
                conditions.append(
                    func.extract("year", PatentPublication.grant_date)
                    <= cohort.grant_year_to
                )
            if cohort.expiry_within_days is not None:
                cutoff = datetime.utcnow().date() + timedelta(
                    days=cohort.expiry_within_days
                )
                conditions.append(
                    and_(
                        PatentPublication.estimated_expiry_date.isnot(None),
                        PatentPublication.estimated_expiry_date <= cutoff,
                        PatentPublication.estimated_expiry_date
                        >= datetime.utcnow().date(),
                    )
                )
            if cohort.has_abstract is True:
                conditions.append(PatentPublication.abstract.isnot(None))
            elif cohort.has_abstract is False:
                conditions.append(PatentPublication.abstract.is_(None))
            if cohort.has_summary is True:
                conditions.append(PatentPublication.summarized_at.isnot(None))
            elif cohort.has_summary is False:
                conditions.append(PatentPublication.summarized_at.is_(None))
            if cohort.has_tags is True:
                conditions.append(PatentPublication.tags.isnot(None))
            elif cohort.has_tags is False:
                conditions.append(PatentPublication.tags.is_(None))
            if cohort.has_opportunity_score is True:
                conditions.append(PatentPublication.opportunity_score.isnot(None))
            elif cohort.has_opportunity_score is False:
                conditions.append(PatentPublication.opportunity_score.is_(None))
            if cohort.min_interesting_score is not None:
                conditions.append(
                    PatentPublication.interesting_score
                    >= cohort.min_interesting_score
                )
            if cohort.max_interesting_score is not None:
                conditions.append(
                    PatentPublication.interesting_score
                    <= cohort.max_interesting_score
                )

            # Per-task-type sensible defaults.
            if task_type == "summary":
                conditions.append(
                    or_(
                        PatentPublication.abstract.isnot(None),
                        PatentPublication.title.isnot(None),
                    )
                )
            elif task_type == "tags":
                # Tagging is only useful once we have a summary; skip the rest.
                conditions.append(PatentPublication.summarized_at.isnot(None))
            elif task_type == "opportunity_score":
                # Opportunity scorer reads tags, claims, expiry. Tags are
                # the most expensive prerequisite; require them so the score
                # isn't based on a near-empty feature set.
                conditions.append(PatentPublication.tags.isnot(None))
            elif task_type == "why_now":
                # Why Now needs tags + opportunity score for rich signals.
                conditions.append(PatentPublication.tags.isnot(None))
                conditions.append(PatentPublication.opportunity_score.isnot(None))
            elif task_type == "opportunity_narrative":
                # Opportunity Narrative needs tags + score for context.
                conditions.append(PatentPublication.tags.isnot(None))
                conditions.append(PatentPublication.opportunity_score.isnot(None))

            if conditions:
                stmt = stmt.where(and_(*conditions))

            stmt = stmt.order_by(PatentPublication.grant_date.desc().nullslast())
            if cohort.limit:
                stmt = stmt.limit(cohort.limit)

    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


# ---------------------------------------------------------------------------
# Cache + token accounting
# ---------------------------------------------------------------------------


def _estimate_summary_tokens(patent: PatentPublication) -> tuple[int, int]:
    """Return (est_input_tokens, est_output_tokens) for a single summary call."""
    payload = build_summary_payload(patent)
    prompt = get_prompt(SUMMARY_PROMPT_NAME, SUMMARY_PROMPT_VERSION)
    rendered_user = prompt.user_template.format(
        schema_description=prompt.schema_description or "",
        **payload,
    )
    input_text = prompt.system + "\n" + rendered_user
    return estimate_tokens(input_text), 900


def _estimate_tag_tokens(patent: PatentPublication) -> tuple[int, int]:
    """Return (est_input_tokens, est_output_tokens) for a single tag call."""
    payload = build_tag_payload(patent)
    prompt = get_prompt(TAG_PROMPT_NAME, TAG_PROMPT_VERSION)
    rendered_user = prompt.user_template.format(
        schema_description=prompt.schema_description or "",
        **payload,
    )
    input_text = prompt.system + "\n" + rendered_user
    # Tag responses are smaller, ~250-450 tokens of JSON.
    return estimate_tokens(input_text), 350


def _estimate_why_now_tokens(patent: PatentPublication) -> tuple[int, int]:
    """Return (est_input_tokens, est_output_tokens) for a single Why Now call."""
    payload = build_why_now_payload(patent)
    prompt = get_prompt(WHY_NOW_PROMPT_NAME, WHY_NOW_PROMPT_VERSION)
    rendered_user = prompt.user_template.format(
        schema_description=prompt.schema_description or "",
        **payload,
    )
    input_text = prompt.system + "\n" + rendered_user
    # Why Now narrative: ~400-600 tokens of structured JSON.
    return estimate_tokens(input_text), 600


def _estimate_opportunity_narrative_tokens(patent: PatentPublication) -> tuple[int, int]:
    """Return (est_input_tokens, est_output_tokens) for a single Opportunity Narrative call."""
    payload = build_opportunity_narrative_payload(patent)
    prompt = get_prompt(OPPORTUNITY_NARRATIVE_PROMPT_NAME, OPPORTUNITY_NARRATIVE_PROMPT_VERSION)
    rendered_user = prompt.user_template.format(
        schema_description=prompt.schema_description or "",
        **payload,
    )
    input_text = prompt.system + "\n" + rendered_user
    # Opportunity Narrative: ~400-700 tokens of structured JSON.
    return estimate_tokens(input_text), 700


def _prompt_for_task(task_type: str):
    """Return a (name, version, hash, model_tier) tuple per task_type.

    For rules-based tasks, ``hash`` is computed from the rules id+version+weights
    via :func:`hash_rules` so cache lookups are consistent with what
    :func:`record_rules_artifact` actually writes.
    """
    if task_type == "summary":
        spec = get_prompt(SUMMARY_PROMPT_NAME, SUMMARY_PROMPT_VERSION)
        return spec.name, spec.version, spec.prompt_hash, "summary"
    if task_type == "tags":
        spec = get_prompt(TAG_PROMPT_NAME, TAG_PROMPT_VERSION)
        return spec.name, spec.version, spec.prompt_hash, "tag"
    if task_type == "opportunity_score":
        rules_hash = hash_rules(
            OPPORTUNITY_RULES_ID, OPPORTUNITY_RULES_VERSION, OPPORTUNITY_WEIGHTS
        )
        return (
            OPPORTUNITY_RULES_ID,
            OPPORTUNITY_RULES_VERSION,
            rules_hash,
            "rules",
        )
    if task_type == "why_now":
        spec = get_prompt(WHY_NOW_PROMPT_NAME, WHY_NOW_PROMPT_VERSION)
        return spec.name, spec.version, spec.prompt_hash, "narrative"
    if task_type == "opportunity_narrative":
        spec = get_prompt(OPPORTUNITY_NARRATIVE_PROMPT_NAME, OPPORTUNITY_NARRATIVE_PROMPT_VERSION)
        return spec.name, spec.version, spec.prompt_hash, "narrative"
    if task_type == "trend_snapshot":
        rules_hash = hash_rules(TREND_RULES_ID, TREND_RULES_VERSION, TREND_WEIGHTS)
        return TREND_RULES_ID, TREND_RULES_VERSION, rules_hash, "rules"
    if task_type == "assignee_intelligence":
        rules_hash = hash_rules(ASSIGNEE_RULES_ID, ASSIGNEE_RULES_VERSION, ASSIGNEE_WEIGHTS)
        return ASSIGNEE_RULES_ID, ASSIGNEE_RULES_VERSION, rules_hash, "rules"
    raise HTTPException(
        status_code=501,
        detail=f"task_type={task_type} not implemented yet.",
    )


async def _count_cached_artifacts(
    db, *, task_type: str, prompt_hash: str, patent_ids: list[UUID]
) -> int:
    """Count complete AIArtifact rows for (task_type, prompt_hash, input_hash in patents)."""
    if not patent_ids:
        return 0
    stmt = (
        select(func.count())
        .select_from(AIArtifact)
        .where(AIArtifact.artifact_type == task_type)
        .where(AIArtifact.prompt_hash == prompt_hash)
        .where(AIArtifact.status == "complete")
        .where(AIArtifact.patent_publication_id.in_(patent_ids))
    )
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


async def _recent_cache_hit_rate(db, *, task_type: str) -> float:
    """Return cache hit-rate for this task_type over the last 7 days."""
    cutoff = datetime.utcnow() - timedelta(days=7)
    stmt = (
        select(
            func.coalesce(func.sum(AIRun.cached_count), 0),
            func.coalesce(func.sum(AIRun.uncached_count), 0),
        )
        .where(AIRun.task_type == task_type)
        .where(AIRun.created_at >= cutoff)
    )
    result = await db.execute(stmt)
    cached, uncached = result.one()
    total = (cached or 0) + (uncached or 0)
    if total == 0:
        return 0.0
    return round(cached / total, 4)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_run(
    request: EstimateRequest,
    db: DbSession,
    settings: AppSettings,
) -> EstimateResponse:
    """Cost-preview for a proposed AI run. Never hits the LLM provider."""
    if request.task_type not in ESTIMATABLE_TASK_TYPES:
        raise HTTPException(
            status_code=501,
            detail=(
                f"Estimator for task_type={request.task_type} is not "
                f"implemented yet. Supported: {sorted(ESTIMATABLE_TASK_TYPES)}."
            ),
        )

    patent_ids = await _resolve_cohort(
        db,
        run_mode=request.run_mode,
        cohort=request.cohort,
        task_type=request.task_type,
    )
    cohort_size = len(patent_ids)

    prompt_name, prompt_version, prompt_hash, model_tier = _prompt_for_task(
        request.task_type
    )
    is_rules = request.task_type in RULES_TASK_TYPES
    model = "rules:v" + str(prompt_version) if is_rules else _model_for_tier(model_tier)

    cached = await _count_cached_artifacts(
        db,
        task_type=request.task_type,
        prompt_hash=prompt_hash,
        patent_ids=patent_ids,
    )
    uncached = max(0, cohort_size - cached)

    # Token + cost estimate. Rules tasks are always $0.
    est_input = 0
    est_output = 0
    est_cost = 0.0
    if not is_rules and uncached > 0:
        sample_ids = patent_ids[: min(20, len(patent_ids))]
        stmt = select(PatentPublication).where(
            PatentPublication.id.in_(sample_ids)
        )
        patents = list((await db.execute(stmt)).scalars().all())
        in_tokens_list: list[int] = []
        out_tokens_list: list[int] = []
        for p in patents:
            if request.task_type == "summary":
                in_t, out_t = _estimate_summary_tokens(p)
            elif request.task_type == "tags":
                in_t, out_t = _estimate_tag_tokens(p)
            elif request.task_type == "why_now":
                in_t, out_t = _estimate_why_now_tokens(p)
            elif request.task_type == "opportunity_narrative":
                in_t, out_t = _estimate_opportunity_narrative_tokens(p)
            else:  # pragma: no cover - guarded above
                in_t, out_t = (0, 0)
            in_tokens_list.append(in_t)
            out_tokens_list.append(out_t)
        if in_tokens_list:
            avg_in = int(sum(in_tokens_list) / len(in_tokens_list))
            avg_out = int(sum(out_tokens_list) / len(out_tokens_list))
            est_input = avg_in * uncached
            est_output = avg_out * uncached
            est_cost = estimate_cost_usd(
                model=model, input_tokens=est_input, output_tokens=est_output
            )

    hit_rate = await _recent_cache_hit_rate(db, task_type=request.task_type)

    requires_confirmation = est_cost > settings.llm_run_auto_approve_usd
    requires_full_batch = (
        request.run_mode == "full_batch"
        or est_cost > settings.llm_run_full_batch_threshold_usd
    )

    return EstimateResponse(
        task_type=request.task_type,
        run_mode=request.run_mode,
        cohort_size=cohort_size,
        cached_count=cached,
        uncached_count=uncached,
        est_input_tokens=est_input,
        est_output_tokens=est_output,
        est_cost_usd=est_cost,
        model=model,
        prompt_name=prompt_name,
        prompt_version=prompt_version,
        prompt_hash=prompt_hash,
        expected_cache_hit_rate_7d=hit_rate,
        auto_approve_threshold_usd=settings.llm_run_auto_approve_usd,
        full_batch_threshold_usd=settings.llm_run_full_batch_threshold_usd,
        requires_confirmation=requires_confirmation,
        requires_full_batch_phrase=requires_full_batch,
    )


@router.post("", response_model=RunSummary)
async def create_run(
    request: CreateRunRequest,
    db: DbSession,
    settings: AppSettings,
) -> RunSummary:
    """Create an AIRun row + enqueue the underlying Celery task.

    Phase 0+1 supports ``summary`` (Sonnet), ``tags`` (Haiku) and
    ``opportunity_score`` (rules, $0). Other task types return 501.
    """
    if request.task_type not in ESTIMATABLE_TASK_TYPES:
        raise HTTPException(
            status_code=501,
            detail=(
                f"Run creation for task_type={request.task_type} lands in a "
                f"later phase. Supported: {sorted(ESTIMATABLE_TASK_TYPES)}."
            ),
        )

    if (
        request.run_mode == "full_batch"
        and request.confirmation_phrase != FULL_BATCH_CONFIRMATION_PHRASE
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Full-batch runs require confirmation_phrase='{FULL_BATCH_CONFIRMATION_PHRASE}'.",
        )

    # Resolve cohort + run estimator identically to the /estimate endpoint.
    estimate = await estimate_run(
        EstimateRequest(
            task_type=request.task_type,
            run_mode=request.run_mode,
            cohort=request.cohort,
            tier=request.tier,
        ),
        db,
        settings,
    )

    if (
        estimate.requires_full_batch_phrase
        and request.confirmation_phrase != FULL_BATCH_CONFIRMATION_PHRASE
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Runs above the full-batch threshold require "
                f"confirmation_phrase='{FULL_BATCH_CONFIRMATION_PHRASE}'."
            ),
        )

    run = AIRun(
        task_type=request.task_type,
        run_mode=request.run_mode,
        cohort_filter=request.cohort.model_dump(mode="json"),
        cohort_size=estimate.cohort_size,
        cached_count=estimate.cached_count,
        uncached_count=estimate.uncached_count,
        model=estimate.model,
        prompt_name=estimate.prompt_name,
        prompt_version=estimate.prompt_version,
        est_input_tokens=estimate.est_input_tokens,
        est_output_tokens=estimate.est_output_tokens,
        est_cost_usd=estimate.est_cost_usd,
        status="pending",
        created_by=settings.default_user_id,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    if request.enqueue:
        patent_ids = await _resolve_cohort(
            db,
            run_mode=request.run_mode,
            cohort=request.cohort,
            task_type=request.task_type,
        )
        enqueued = _dispatch_celery_per_patent(
            task_type=request.task_type,
            patent_ids=patent_ids,
            run_id=str(run.id),
        )
        logger.info(
            "AIRun %s enqueued %d %s tasks (cohort_size=%d)",
            run.id,
            enqueued,
            request.task_type,
            estimate.cohort_size,
        )
        run.status = "running"
        run.started_at = datetime.utcnow()
        await db.commit()
        await db.refresh(run)

    return RunSummary.model_validate(run, from_attributes=True)


def _dispatch_celery_per_patent(
    *, task_type: str, patent_ids: list[UUID], run_id: str
) -> int:
    """Fan out one Celery task per patent for the given task_type.

    Returns the number of tasks enqueued. Each task is responsible for
    cache lookup + denormalization, so re-running an AIRun is idempotent.
    """
    if task_type == "summary":
        from app.tasks.summarize import summarize_patent as task

        for pid in patent_ids:
            task.delay(str(pid))
        return len(patent_ids)

    if task_type == "tags":
        from app.tasks.tag import tag_patent as task

        for pid in patent_ids:
            task.delay(str(pid), run_id)
        return len(patent_ids)

    if task_type == "opportunity_score":
        from app.tasks.opportunity import score_patent_opportunity_task as task

        for pid in patent_ids:
            task.delay(str(pid), run_id)
        return len(patent_ids)

    if task_type == "why_now":
        from app.tasks.why_now import generate_why_now as task

        for pid in patent_ids:
            task.delay(str(pid), run_id)
        return len(patent_ids)

    if task_type == "opportunity_narrative":
        from app.tasks.opportunity_narrative import generate_opportunity_narrative as task

        for pid in patent_ids:
            task.delay(str(pid), run_id)
        return len(patent_ids)

    if task_type == "trend_snapshot":
        from app.tasks.trend_snapshot import generate_trend_snapshot_task as task

        for pid in patent_ids:
            task.delay(str(pid), run_id)
        return len(patent_ids)

    if task_type == "assignee_intelligence":
        from app.tasks.assignee_intelligence import generate_assignee_intelligence_task as task

        for pid in patent_ids:
            task.delay(str(pid), run_id)
        return len(patent_ids)

    raise HTTPException(
        status_code=501,
        detail=f"No Celery dispatcher for task_type={task_type}.",
    )


@router.get("", response_model=RunListResponse)
async def list_runs(
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
    task_type: str | None = Query(default=None),
) -> RunListResponse:
    """Most-recent runs first."""
    stmt = select(AIRun).order_by(AIRun.created_at.desc()).limit(limit)
    if task_type:
        stmt = stmt.where(AIRun.task_type == task_type)
    result = await db.execute(stmt)
    runs = list(result.scalars().all())
    items = [RunSummary.model_validate(r, from_attributes=True) for r in runs]
    count_stmt = select(func.count()).select_from(AIRun)
    if task_type:
        count_stmt = count_stmt.where(AIRun.task_type == task_type)
    total = int((await db.execute(count_stmt)).scalar_one() or 0)
    return RunListResponse(items=items, total=total)


@router.get("/{run_id}", response_model=RunSummary)
async def get_run(run_id: UUID, db: DbSession) -> RunSummary:
    stmt = select(AIRun).where(AIRun.id == run_id)
    run = (await db.execute(stmt)).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="AIRun not found")
    return RunSummary.model_validate(run, from_attributes=True)


class ArtifactSummary(BaseModel):
    id: UUID
    patent_publication_id: UUID | None
    artifact_type: str
    artifact_version: int
    model: str
    prompt_name: str
    prompt_version: int
    status: str
    input_tokens: int
    output_tokens: int
    actual_cost_usd: float
    content_json_preview: dict | None
    created_at: datetime


class ArtifactListResponse(BaseModel):
    items: list[ArtifactSummary]
    total: int


@router.get("/{run_id}/artifacts", response_model=ArtifactListResponse)
async def get_run_artifacts(
    run_id: UUID,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ArtifactListResponse:
    run = (await db.execute(select(AIRun).where(AIRun.id == run_id))).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="AIRun not found")

    total_stmt = (
        select(func.count())
        .select_from(AIArtifact)
        .where(AIArtifact.run_id == run_id)
    )
    total = int((await db.execute(total_stmt)).scalar_one() or 0)

    stmt = (
        select(AIArtifact)
        .where(AIArtifact.run_id == run_id)
        .order_by(AIArtifact.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = list((await db.execute(stmt)).scalars().all())

    items = []
    for a in rows:
        preview = None
        if a.content_json:
            preview = _truncate_json_preview(a.content_json)
        items.append(
            ArtifactSummary(
                id=a.id,
                patent_publication_id=a.patent_publication_id,
                artifact_type=a.artifact_type,
                artifact_version=a.artifact_version,
                model=a.model,
                prompt_name=a.prompt_name,
                prompt_version=a.prompt_version,
                status=a.status,
                input_tokens=a.input_tokens,
                output_tokens=a.output_tokens,
                actual_cost_usd=a.actual_cost_usd,
                content_json_preview=preview,
                created_at=a.created_at,
            )
        )

    return ArtifactListResponse(items=items, total=total)


def _truncate_json_preview(obj: dict, max_keys: int = 20, max_str_len: int = 200) -> dict:
    """Return a shallow-truncated copy of a dict for UI preview."""
    preview: dict = {}
    for i, (k, v) in enumerate(obj.items()):
        if i >= max_keys:
            preview["…"] = f"{len(obj) - max_keys} more keys"
            break
        if isinstance(v, str) and len(v) > max_str_len:
            preview[k] = v[:max_str_len] + "…"
        elif isinstance(v, list) and len(v) > 10:
            preview[k] = v[:10] + [f"… ({len(v) - 10} more)"]
        elif isinstance(v, dict):
            preview[k] = _truncate_json_preview(v, max_keys=10, max_str_len=100)
        else:
            preview[k] = v
    return preview


# ---------------------------------------------------------------------------
# Metadata helpers (used by the frontend dropdowns)
# ---------------------------------------------------------------------------


class RunMetadata(BaseModel):
    task_types: list[str]
    run_modes: list[str]
    auto_approve_threshold_usd: float
    full_batch_threshold_usd: float
    default_user_id: str
    llm_mode: str


@router.get("/meta/options", response_model=RunMetadata)
async def run_metadata(settings: AppSettings) -> RunMetadata:
    return RunMetadata(
        task_types=list(ARTIFACT_TYPES),
        run_modes=list(RUN_MODES),
        auto_approve_threshold_usd=settings.llm_run_auto_approve_usd,
        full_batch_threshold_usd=settings.llm_run_full_batch_threshold_usd,
        default_user_id=settings.default_user_id,
        llm_mode=settings.llm_mode,
    )
