from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_models import AIArtifact, AIRun, User
from app.tasks.run_aggregates import recompute_run_aggregates


@pytest.mark.asyncio
async def test_recompute_run_aggregates_counts_cached_artifacts_as_completed(
    db_session: AsyncSession,
) -> None:
    user_id = "local-user"
    db_session.add(User(id=user_id, display_name="Local User", email=None))
    run = AIRun(
        task_type="tags",
        run_mode="cohort",
        cohort_filter={},
        cohort_size=2,
        cached_count=1,
        uncached_count=1,
        model="claude-haiku-4-5",
        prompt_name="tag_patent",
        prompt_version=1,
        est_input_tokens=10,
        est_output_tokens=5,
        est_cost_usd=0.01,
        status="running",
        created_by=user_id,
    )
    db_session.add(run)
    await db_session.flush()
    db_session.add(
        AIArtifact(
            run_id=run.id,
            artifact_type="tags",
            artifact_version=1,
            model="claude-haiku-4-5",
            prompt_name="tag_patent",
            prompt_version=1,
            prompt_hash="prompt-hash",
            input_hash=f"input-hash-{uuid4()}",
            input_tokens=10,
            output_tokens=5,
            actual_cost_usd=0.01,
            status="complete",
        )
    )
    await db_session.commit()

    await recompute_run_aggregates(db_session, run.id)
    await db_session.refresh(run)

    assert run.completed_count == 2
    assert run.failed_count == 0
    assert run.actual_input_tokens == 10
    assert run.actual_output_tokens == 5
    assert run.actual_cost_usd == 0.01
    assert run.status == "succeeded"
    assert run.finished_at is not None
