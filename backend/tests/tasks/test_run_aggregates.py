from uuid import uuid4

import pytest

from app.tasks import run_aggregates


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeUpdate:
    def __init__(self):
        self.update_values = {}

    def where(self, *args, **kwargs):
        return self

    def values(self, **kwargs):
        self.update_values = kwargs
        return self


class _FakeSession:
    def __init__(self, run, rows):
        self._run = run
        self._rows = rows
        self._select_count = 0
        self.updated_values = {}
        self.committed = False

    async def execute(self, stmt):
        if isinstance(stmt, _FakeUpdate):
            self.updated_values = stmt.update_values
            return _ScalarResult(None)

        self._select_count += 1
        if self._select_count == 1:
            return _ScalarResult(self._run)
        return _RowsResult(self._rows)

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_recompute_run_aggregates_waits_for_cached_task_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid4()
    run = type(
        "Run",
        (),
        {
            "id": run_id,
            "status": "running",
            "cohort_size": 4,
            "cached_count": 2,
            "finished_at": None,
        },
    )()
    session = _FakeSession(
        run,
        rows=[
            ("complete", 1, 100, 50, 0.01),
            ("failed", 1, 0, 0, 0.0),
        ],
    )

    update_statements: list[_FakeUpdate] = []

    def fake_update(_model):
        statement = _FakeUpdate()
        update_statements.append(statement)
        return statement

    monkeypatch.setattr(run_aggregates, "update", fake_update)

    await run_aggregates.recompute_run_aggregates(session, run_id)

    assert session.committed is True
    assert session.updated_values["completed_count"] == 1
    assert session.updated_values["failed_count"] == 1
    assert session.updated_values["actual_input_tokens"] == 100
    assert session.updated_values["actual_output_tokens"] == 50
    assert session.updated_values["actual_cost_usd"] == 0.01
    assert session.updated_values["status"] == "running"
    assert session.updated_values["finished_at"] is None
    assert len(update_statements) == 1


@pytest.mark.asyncio
async def test_recompute_run_aggregates_preserves_recorded_task_completions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid4()
    run = type(
        "Run",
        (),
        {
            "id": run_id,
            "status": "running",
            "cohort_size": 2,
            "cached_count": 0,
            "completed_count": 2,
            "finished_at": None,
        },
    )()
    session = _FakeSession(run, rows=[("complete", 1, 100, 50, 0.01)])

    def fake_update(_model):
        return _FakeUpdate()

    monkeypatch.setattr(run_aggregates, "update", fake_update)

    await run_aggregates.recompute_run_aggregates(session, run_id)

    assert session.updated_values["completed_count"] == 2
    assert session.updated_values["status"] == "succeeded"


@pytest.mark.asyncio
async def test_recompute_run_aggregates_finishes_empty_cohort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = uuid4()
    run = type(
        "Run",
        (),
        {
            "id": run_id,
            "status": "running",
            "cohort_size": 0,
            "cached_count": 0,
            "completed_count": 0,
            "finished_at": None,
        },
    )()
    session = _FakeSession(run, rows=[])

    def fake_update(_model):
        return _FakeUpdate()

    monkeypatch.setattr(run_aggregates, "update", fake_update)

    await run_aggregates.recompute_run_aggregates(session, run_id)

    assert session.updated_values["completed_count"] == 0
    assert session.updated_values["status"] == "succeeded"
