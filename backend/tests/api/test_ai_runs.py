"""Tests for the /api/v1/ai-runs estimate + run-history endpoints."""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_settings
from app.config import Settings
from app.core.ai_models import AIRun, User
from app.core.models import PatentPublication
from app.main import app


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


@pytest.mark.asyncio
async def test_expensive_cohort_requires_full_batch_confirmation_phrase(
    db_session: AsyncSession,
    client: AsyncClient,
    test_settings: Settings,
) -> None:
    db_session.add(
        User(
            id=test_settings.default_user_id,
            display_name=test_settings.default_user_display_name,
            email=None,
        )
    )
    await _seed_patents(db_session, n=1)
    strict_settings = test_settings.model_copy(
        update={
            "llm_run_auto_approve_usd": 0.0,
            "llm_run_full_batch_threshold_usd": 0.0,
        }
    )
    app.dependency_overrides[get_settings] = lambda: strict_settings
    try:
        body = {
            "task_type": "summary",
            "run_mode": "cohort",
            "cohort": {"has_abstract": True},
            "enqueue": False,
        }
        r = await client.post("/api/v1/ai-runs", json=body)
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert r.status_code == 400
    assert "RUN FULL BATCH" in r.json()["detail"]


def test_summary_dispatch_passes_run_id_to_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.v1.ai_runs import _dispatch_celery_per_patent
    from app.tasks import summarize as summarize_tasks

    patent_id = uuid4()
    run_id = str(uuid4())
    calls: list[tuple[str, str]] = []

    def fake_delay(*args: str) -> None:
        calls.append(args)

    monkeypatch.setattr(summarize_tasks.summarize_patent, "delay", fake_delay)

    enqueued = _dispatch_celery_per_patent(
        task_type="summary",
        patent_ids=[patent_id],
        run_id=run_id,
    )

    assert enqueued == 1
    assert calls == [(str(patent_id), run_id)]


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
