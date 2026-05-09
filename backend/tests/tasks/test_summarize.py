from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.models import PatentPublication


class TestSummarizePatent:
    @patch("app.tasks.summarize._summarize_patent_async")
    def test_summarize_returns_success(self, mock_summarize_async: MagicMock) -> None:
        import asyncio

        async def mock_result():
            return {"status": "success", "summary": {"what_it_is": "Test"}}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        mock_summarize_async.return_value = loop.run_until_complete(mock_result())

    @patch("app.tasks.summarize._summarize_patent_async")
    def test_summarize_handles_not_found(self, mock_summarize_async: MagicMock) -> None:
        import asyncio

        async def mock_result():
            return {"status": "failed", "error": "Patent not found"}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        mock_summarize_async.return_value = loop.run_until_complete(mock_result())


class TestBatchSummarize:
    @patch("app.tasks.summarize._get_pending_patents")
    def test_batch_summarize_empty_queue(self, mock_get_pending: MagicMock) -> None:
        import asyncio

        async def mock_result():
            return []

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        mock_get_pending.return_value = loop.run_until_complete(mock_result())


class _SessionResult:
    def __init__(self, patent: PatentPublication):
        self._patent = patent

    def scalar_one_or_none(self) -> PatentPublication:
        return self._patent


class _SummarySession:
    def __init__(self, patent: PatentPublication):
        self._patent = patent
        self.committed = False

    async def execute(self, _stmt):
        return _SessionResult(self._patent)

    async def commit(self):
        self.committed = True


class _SummarySessionContext:
    def __init__(self, session: _SummarySession):
        self._session = session

    async def __aenter__(self) -> _SummarySession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.asyncio
async def test_summarize_patent_async_links_summary_artifact_to_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.tasks.summarize as summarize_tasks

    patent_id = uuid4()
    run_uuid = uuid4()
    artifact_id = uuid4()
    patent = PatentPublication(
        id=patent_id,
        doc_id="USPTO:SUMMARY-RUN",
        office="USPTO",
        publication_number="SUMMARY-RUN",
        title="Run-linked summary",
        abstract="Abstract",
    )
    session = _SummarySession(patent)
    summary = {
        "what_it_is": "A test invention",
        "problem_solved": "Test problem",
        "how_it_works": "Test mechanism",
        "commercial_significance": "Test significance",
        "who_should_care": ["Engineers"],
        "novel_applications": [{"application": "Test app"}],
        "confidence_note": "High",
        "source_spans": [],
    }
    recompute_calls: list[str] = []

    async def fake_cached_summarize(session_arg, patent_arg, *, run_id: str):
        assert session_arg is session
        assert patent_arg is patent
        assert str(run_id) == str(run_uuid)
        return summary, artifact_id

    async def fake_recompute(session_arg, run_id_arg):
        assert session_arg is session
        recompute_calls.append(str(run_id_arg))

    monkeypatch.setattr(
        summarize_tasks,
        "async_session_maker",
        lambda: _SummarySessionContext(session),
    )
    monkeypatch.setattr(
        summarize_tasks,
        "cached_summarize_patent",
        fake_cached_summarize,
    )
    monkeypatch.setattr(
        summarize_tasks,
        "recompute_run_aggregates",
        fake_recompute,
        raising=False,
    )

    result = await summarize_tasks._summarize_patent_async(
        str(patent_id),
        run_id=str(run_uuid),
    )

    assert result["status"] == "success"
    assert result["artifact_id"] == str(artifact_id)
    assert patent.latest_summary_artifact_id == artifact_id
    assert session.committed is True
    assert recompute_calls == [str(run_uuid)]


@pytest.mark.asyncio
async def test_summarize_patent_async_recomputes_run_when_summary_skips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.tasks.summarize as summarize_tasks

    patent_id = uuid4()
    run_uuid = uuid4()
    patent = PatentPublication(
        id=patent_id,
        doc_id="USPTO:SUMMARY-SKIP",
        office="USPTO",
        publication_number="SUMMARY-SKIP",
        title="Already summarized",
        abstract="Abstract",
        summarized_at=datetime.utcnow(),
    )
    session = _SummarySession(patent)
    recompute_calls: list[str] = []

    async def fake_recompute(session_arg, run_id_arg):
        assert session_arg is session
        recompute_calls.append(str(run_id_arg))

    monkeypatch.setattr(
        summarize_tasks,
        "async_session_maker",
        lambda: _SummarySessionContext(session),
    )
    monkeypatch.setattr(
        summarize_tasks,
        "recompute_run_aggregates",
        fake_recompute,
    )

    result = await summarize_tasks._summarize_patent_async(
        str(patent_id),
        run_id=str(run_uuid),
    )

    assert result == {"status": "skipped", "reason": "already_summarized"}
    assert recompute_calls == [str(run_uuid)]
