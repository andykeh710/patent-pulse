from datetime import datetime
from uuid import uuid4

import pytest

from app.core.ai_models import AIRun
from app.tasks.run_aggregates import recompute_run_aggregates


class _ScalarResult:
    def __init__(self, value: AIRun | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> AIRun | None:
        return self.value


class _RowsResult:
    def __init__(self, rows: list[tuple]) -> None:
        self.rows = rows

    def all(self) -> list[tuple]:
        return self.rows


class _FakeSession:
    def __init__(self, run: AIRun, rows: list[tuple]) -> None:
        self.run = run
        self.rows = rows
        self.updated_values: dict[str, object] = {}
        self.commits = 0
        self._execute_count = 0

    async def execute(self, statement):
        self._execute_count += 1
        if self._execute_count == 1:
            return _ScalarResult(self.run)
        if self._execute_count == 2:
            return _RowsResult(self.rows)

        self.updated_values = {
            column.key: bind.value for column, bind in statement._values.items()
        }
        return _RowsResult([])

    async def commit(self) -> None:
        self.commits += 1


@pytest.mark.asyncio
async def test_recompute_counts_cached_artifacts_as_completed() -> None:
    artifact_id = uuid4()
    run = AIRun(
        id=uuid4(),
        task_type="summary",
        run_mode="cohort",
        cohort_filter={},
        cohort_size=3,
        cached_count=2,
        uncached_count=1,
        model="claude-sonnet-4-20250514",
        prompt_name="summarize",
        prompt_version=1,
        status="running",
        created_by="local-user",
        started_at=datetime.utcnow(),
    )
    session = _FakeSession(run, [("complete", None, artifact_id, 10, 20, 0.03)])

    await recompute_run_aggregates(session, run.id)

    assert session.updated_values["completed_count"] == 3
    assert session.updated_values["failed_count"] == 0
    assert session.updated_values["actual_cost_usd"] == 0.03
    assert session.updated_values["status"] == "succeeded"
    assert session.updated_values["finished_at"] is not None
    assert session.commits == 1


@pytest.mark.asyncio
async def test_recompute_counts_retried_failures_once_per_patent() -> None:
    patent_id = uuid4()
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
        created_by="local-user",
        started_at=datetime.utcnow(),
    )
    session = _FakeSession(
        run,
        [
            ("failed", patent_id, uuid4(), 0, 0, 0.0),
            ("failed", patent_id, uuid4(), 0, 0, 0.0),
        ],
    )

    await recompute_run_aggregates(session, run.id)

    assert session.updated_values["completed_count"] == 0
    assert session.updated_values["failed_count"] == 1
    assert session.updated_values["status"] == "failed"
    assert session.updated_values["finished_at"] is not None


@pytest.mark.asyncio
async def test_recompute_prefers_complete_after_retry_failure() -> None:
    patent_id = uuid4()
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
        created_by="local-user",
        started_at=datetime.utcnow(),
    )
    session = _FakeSession(
        run,
        [
            ("failed", patent_id, uuid4(), 0, 0, 0.0),
            ("complete", patent_id, uuid4(), 10, 20, 0.03),
        ],
    )

    await recompute_run_aggregates(session, run.id)

    assert session.updated_values["completed_count"] == 1
    assert session.updated_values["failed_count"] == 0
    assert session.updated_values["status"] == "succeeded"


@pytest.mark.asyncio
async def test_recompute_corrects_terminal_status_after_cache_invalidation() -> None:
    patent_id = uuid4()
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
        status="succeeded",
        created_by="local-user",
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    session = _FakeSession(
        run,
        [("failed", patent_id, uuid4(), 10, 20, 0.03)],
    )

    await recompute_run_aggregates(session, run.id)

    assert session.updated_values["completed_count"] == 0
    assert session.updated_values["failed_count"] == 1
    assert session.updated_values["status"] == "failed"
