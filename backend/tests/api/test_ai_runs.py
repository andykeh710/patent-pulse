"""Tests for the /api/v1/ai-runs estimate + run-history endpoints."""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.ai_runs import (
    CreateRunRequest,
    EstimateResponse,
    _dispatch_celery_per_patent,
    _require_full_batch_confirmation,
)
from app.core.ai_models import AIArtifact, AIRun, User
from app.core.models import PatentPublication
from app.tasks.run_aggregates import recompute_run_aggregates


async def _seed_patents(session: AsyncSession, n: int = 5) -> list[PatentPublication]:
    patents: list[PatentPublication] = []
    for i in range(n):
        p = PatentPublication(
            id=uuid4(),
            doc_id=f"USPTO:RUN{i:03d}",
            office="USPTO",
            publication_number=f"RUN{i:03d}",
            title=f"Test patent {i}",
            abstract="Some abstract content here.",
            cpc=["G06F 21/00"],
            grant_date=date(2022, 1, 1),
        )
        session.add(p)
        patents.append(p)
    await session.commit()
    return patents


@pytest.mark.asyncio
async def test_estimate_summary_dev_fixture_returns_zero_cost_when_no_patents(
    client: AsyncClient,
) -> None:
    body = {"task_type": "summary", "run_mode": "dev_fixture", "cohort": {}}
    r = await client.post("/api/v1/ai-runs/estimate", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["cohort_size"] == 0
    assert data["est_cost_usd"] == 0.0
    assert data["model"]
    assert data["prompt_name"] == "summarize"


@pytest.mark.asyncio
async def test_estimate_summary_with_seeded_patents(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_patents(db_session, n=3)
    body = {
        "task_type": "summary",
        "run_mode": "cohort",
        "cohort": {"has_abstract": True},
    }
    r = await client.post("/api/v1/ai-runs/estimate", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["cohort_size"] == 3
    assert data["uncached_count"] == 3
    assert data["cached_count"] == 0
    assert data["est_input_tokens"] > 0
    assert data["est_cost_usd"] >= 0


@pytest.mark.asyncio
async def test_estimate_unsupported_task_type_returns_501(client: AsyncClient) -> None:
    # patent_cliff_analysis is Phase 6+; not yet estimatable.
    body = {"task_type": "patent_cliff_analysis", "run_mode": "dev_fixture", "cohort": {}}
    r = await client.post("/api/v1/ai-runs/estimate", json=body)
    assert r.status_code == 501


@pytest.mark.asyncio
async def test_estimate_tags_for_summarized_patents(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    """``tags`` (Haiku) cohort is gated on patents that already have a summary."""
    from datetime import datetime

    patents = await _seed_patents(db_session, n=3)
    # Mark two as summarized so they qualify for tagging.
    patents[0].summarized_at = datetime.utcnow()
    patents[1].summarized_at = datetime.utcnow()
    await db_session.commit()

    body = {"task_type": "tags", "run_mode": "cohort", "cohort": {}}
    r = await client.post("/api/v1/ai-runs/estimate", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["cohort_size"] == 2  # only the summarized ones
    assert data["uncached_count"] == 2
    assert data["prompt_name"] == "tag_patent"
    assert data["est_input_tokens"] > 0
    # Haiku is cheaper than Sonnet → cost should be non-zero but small.
    assert 0 < data["est_cost_usd"] < 1.0


@pytest.mark.asyncio
async def test_estimate_opportunity_score_is_rules_and_free(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    """``opportunity_score`` is rules-only — always $0 with model='rules:v<n>'."""
    patents = await _seed_patents(db_session, n=3)
    # Rules cohort requires tags denormalized.
    for p in patents[:2]:
        p.tags = {
            "industries": ["ai_ml"],
            "problem_solved": "x",
            "technology_method": ["machine_learning"],
            "materials": [],
            "novel_application_categories": [],
            "time_horizon": "near_term",
            "risk_flags": [],
            "opportunity_tags": ["startup_opportunity"],
            "trend_tags": [],
        }
    await db_session.commit()

    body = {"task_type": "opportunity_score", "run_mode": "cohort", "cohort": {}}
    r = await client.post("/api/v1/ai-runs/estimate", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["cohort_size"] == 2
    assert data["est_cost_usd"] == 0.0
    assert data["est_input_tokens"] == 0
    assert data["est_output_tokens"] == 0
    assert data["model"].startswith("rules:v")
    assert data["prompt_name"] == "opportunity_score_rules"


@pytest.mark.asyncio
async def test_full_batch_requires_confirmation_phrase(
    db_session: AsyncSession, client: AsyncClient
) -> None:
    await _seed_patents(db_session, n=2)
    body = {
        "task_type": "summary",
        "run_mode": "full_batch",
        "cohort": {},
        "confirmation_phrase": "wrong phrase",
        "enqueue": False,
    }
    r = await client.post("/api/v1/ai-runs", json=body)
    assert r.status_code == 400
    assert "RUN FULL BATCH" in r.json()["detail"]


def _estimate_response(
    *,
    requires_full_batch_phrase: bool,
    requires_confirmation: bool = False,
) -> EstimateResponse:
    return EstimateResponse(
        task_type="summary",
        run_mode="cohort",
        cohort_size=10,
        cached_count=0,
        uncached_count=10,
        est_input_tokens=10_000,
        est_output_tokens=5_000,
        est_cost_usd=30.0,
        model="claude-sonnet-4-20250514",
        prompt_name="summarize",
        prompt_version=1,
        prompt_hash="abc123",
        expected_cache_hit_rate_7d=0.0,
        auto_approve_threshold_usd=5.0,
        full_batch_threshold_usd=25.0,
        requires_confirmation=requires_confirmation,
        requires_full_batch_phrase=requires_full_batch_phrase,
    )


def test_estimated_full_batch_risk_requires_confirmation_phrase() -> None:
    request = CreateRunRequest(
        task_type="summary",
        run_mode="cohort",
        cohort={},
        enqueue=False,
    )

    with pytest.raises(HTTPException) as exc:
        _require_full_batch_confirmation(
            request,
            _estimate_response(requires_full_batch_phrase=True),
        )

    assert exc.value.status_code == 400
    assert "RUN FULL BATCH" in exc.value.detail


def test_dispatch_summary_tasks_include_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.tasks import summarize as summarize_tasks

    patent_id = uuid4()
    calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(
        summarize_tasks.summarize_patent,
        "delay",
        lambda *args: calls.append(args),
    )

    enqueued = _dispatch_celery_per_patent(
        task_type="summary",
        patent_ids=[patent_id],
        run_id="run-123",
    )

    assert enqueued == 1
    assert calls == [(str(patent_id), "run-123", True)]


@pytest.mark.asyncio
async def test_recompute_run_aggregates_ignores_estimated_cache_hits_without_artifact(
    db_session: AsyncSession,
) -> None:
    user = User(
        id="test-user",
        display_name="Test User",
        email=None,
        preferences={},
    )
    run = AIRun(
        id=uuid4(),
        task_type="tags",
        run_mode="cohort",
        cohort_filter={},
        cohort_size=2,
        cached_count=1,
        uncached_count=1,
        model="claude-haiku-4-5",
        prompt_name="tag_patent",
        prompt_version=1,
        status="running",
        created_by=user.id,
    )
    artifact = AIArtifact(
        id=uuid4(),
        run_id=run.id,
        artifact_type="tags",
        artifact_version=1,
        model="claude-haiku-4-5",
        prompt_name="tag_patent",
        prompt_version=1,
        prompt_hash="prompt",
        input_hash="input",
        content_json={"industries": []},
        status="complete",
    )
    db_session.add_all([user, run, artifact])
    await db_session.commit()

    await recompute_run_aggregates(db_session, run.id)
    await db_session.refresh(run)

    assert run.completed_count == 1
    assert run.failed_count == 0
    assert run.status == "running"


@pytest.mark.asyncio
async def test_runs_list_initially_empty(client: AsyncClient) -> None:
    r = await client.get("/api/v1/ai-runs")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_runs_metadata_options(client: AsyncClient) -> None:
    r = await client.get("/api/v1/ai-runs/meta/options")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data["task_types"]
    assert "dev_fixture" in data["run_modes"]
    assert data["auto_approve_threshold_usd"] > 0
