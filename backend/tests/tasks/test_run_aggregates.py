from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import AIRun, User
from app.tasks.run_aggregates import recompute_run_aggregates, record_run_item_failed


@pytest.mark.asyncio
async def test_recompute_run_aggregates_counts_cached_work(
    db_session: AsyncSession,
) -> None:
    user = User(
        id="local-user",
        display_name="Local User",
        email=None,
        preferences={},
    )
    run = AIRun(
        id=uuid4(),
        task_type="summary",
        run_mode="cohort",
        cohort_filter={},
        cohort_size=2,
        cached_count=2,
        uncached_count=0,
        model="claude-sonnet-4-20250514",
        prompt_name="summarize",
        prompt_version=1,
        status="running",
        created_by=user.id,
    )
    db_session.add(user)
    db_session.add(run)
    await db_session.commit()

    await recompute_run_aggregates(db_session, run.id)
    await db_session.refresh(run)

    assert run.completed_count == 2
    assert run.failed_count == 0
    assert run.status == "succeeded"
    assert run.finished_at is not None


@pytest.mark.asyncio
async def test_record_run_item_failed_finishes_uncached_run(
    db_session: AsyncSession,
) -> None:
    user = User(
        id="local-user",
        display_name="Local User",
        email=None,
        preferences={},
    )
    run = AIRun(
        id=uuid4(),
        task_type="summary",
        run_mode="cohort",
        cohort_filter={},
        cohort_size=1,
        cached_count=0,
        uncached_count=1,
        model="claude-sonnet-4-20250514",
        prompt_name="summarize",
        prompt_version=1,
        status="running",
        created_by=user.id,
    )
    db_session.add(user)
    db_session.add(run)
    await db_session.commit()

    await record_run_item_failed(db_session, run.id)
    await db_session.refresh(run)

    assert run.completed_count == 0
    assert run.failed_count == 1
    assert run.status == "failed"
    assert run.finished_at is not None
