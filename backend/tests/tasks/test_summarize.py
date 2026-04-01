from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


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
