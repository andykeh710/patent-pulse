"""
Google Patents provider.

Wraps the existing GooglePatentsClient for abstract/claims enrichment
and WO record fallback.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import date
from typing import Any

from app.ingestion.google_patents_client import GooglePatentsClient
from app.patent_sources.base import BasePatentProvider
from app.patent_sources.registry import register

logger = logging.getLogger(__name__)


class GooglePatentsProvider(BasePatentProvider):
    """Google Patents enrichment provider."""

    name = "google_patents"

    def fetch_by_publication_number(self, publication_number: str) -> dict[str, Any] | None:
        with GooglePatentsClient() as client:
            result = client.fetch_patent_fulltext(publication_number)
            if result.get("abstract"):
                return {
                    "publication_number": publication_number,
                    "abstract": result["abstract"],
                    "claims_text": result.get("claims_text"),
                }
            return None

    def search_by_publication_date(
        self, publication_date: date, max_results: int = 100
    ) -> Iterator[dict[str, Any]]:
        # Google Patents is not a search-by-date source — no bulk search.
        if False:
            yield {}


# Auto-register
register(GooglePatentsProvider.name, GooglePatentsProvider())
