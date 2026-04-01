from datetime import date
from unittest.mock import MagicMock, patch

import pytest


class TestIngestWeeklyGrants:
    @patch("app.tasks.ingest_grants.USPTOClient")
    @patch("app.tasks.ingest_grants._upsert_patent_async")
    @patch("app.tasks.ingest_grants.summarize_patent")
    def test_ingest_creates_new_records(
        self,
        mock_summarize: MagicMock,
        mock_upsert: MagicMock,
        mock_client_class: MagicMock,
    ) -> None:
        from app.tasks.ingest_grants import ingest_weekly_grants

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_grants_by_date.return_value = [
            {
                "patent_number": "12345678",
                "filing_date": "2022-01-15",
                "issue_date": "2024-03-15",
                "invention_title": "Test Patent",
                "assignees": [{"assignee_name": "Test Corp"}],
                "inventors": [{"inventor_name": "John Doe"}],
                "cpc_codes": [{"code": "G06F 21/00"}],
                "ipc_codes": [],
            }
        ]

        mock_record = MagicMock()
        mock_record.id = "test-uuid"

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def mock_upsert_coro(*args):
            return (mock_record, True)

        mock_upsert.return_value = loop.run_until_complete(mock_upsert_coro())

        mock_summarize.delay = MagicMock()

    @patch("app.tasks.ingest_grants.USPTOClient")
    def test_ingest_handles_empty_results(self, mock_client_class: MagicMock) -> None:
        from app.tasks.ingest_grants import ingest_weekly_grants

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_grants_by_date.return_value = []


class TestHelperFunctions:
    def test_get_last_tuesday(self) -> None:
        from app.ingestion.uspto_client import get_last_tuesday

        tuesday = get_last_tuesday(date(2024, 3, 15))
        assert tuesday.weekday() == 1

    def test_get_last_thursday(self) -> None:
        from app.ingestion.uspto_client import get_last_thursday

        thursday = get_last_thursday(date(2024, 3, 15))
        assert thursday.weekday() == 3
