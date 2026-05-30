"""
WIPO PATENTSCOPE patent data provider.

Wraps the existing WIPOClient with the BasePatentProvider interface.
Currently returns 403 on search — use ScrapeGraph as fallback.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import date
from typing import Any

from app.ingestion.wipo_client import WIPOClient, get_last_thursday
from app.patent_sources.base import BasePatentProvider
from app.patent_sources.registry import register

logger = logging.getLogger(__name__)


class WIPOProvider(BasePatentProvider):
    """WIPO PATENTSCOPE provider."""

    name = "wipo"

    def fetch_by_publication_number(self, publication_number: str) -> dict[str, Any] | None:
        with WIPOClient() as client:
            return client.fetch_pct_publication(publication_number)

    def search_by_publication_date(
        self, publication_date: date, max_results: int = 100
    ) -> Iterator[dict[str, Any]]:
        with WIPOClient() as client:
            yield from client.search_pct_by_date(publication_date, max_results)


# Auto-register
register(WIPOProvider.name, WIPOProvider())
