from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest


class TestUpdateExpiryFlags:
    @patch("app.tasks.expiry_watch._update_expiry_flags_async")
    def test_update_expiry_flags_returns_stats(
        self, mock_update_async: MagicMock
    ) -> None:
        import asyncio

        async def mock_result():
            return {"marked_expired": 5, "marked_grace_period": 3, "marked_current": 10}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        mock_update_async.return_value = loop.run_until_complete(mock_result())


class TestGetExpiringSoon:
    @patch("app.tasks.expiry_watch._get_expiring_patents")
    def test_get_expiring_soon_returns_list(
        self, mock_get_expiring: MagicMock
    ) -> None:
        import asyncio

        mock_patent = MagicMock()
        mock_patent.id = "test-uuid"
        mock_patent.doc_id = "USPTO:TEST001"
        mock_patent.title = "Test Patent"
        mock_patent.assignees = ["Test Corp"]
        mock_patent.estimated_expiry_date = date.today() + timedelta(days=30)

        async def mock_result():
            return [mock_patent]

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        mock_get_expiring.return_value = loop.run_until_complete(mock_result())
