"""
EPO OPS patent data provider.

Wraps the existing EPOClient with the BasePatentProvider interface.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import date
from typing import Any

from app.ingestion.epo_client import EPOClient
from app.patent_sources.base import BasePatentProvider
from app.patent_sources.registry import register

logger = logging.getLogger(__name__)


class EPOOPSProvider(BasePatentProvider):
    """EPO Open Patent Services provider."""

    name = "epo_ops"

    def fetch_by_publication_number(self, publication_number: str) -> dict[str, Any] | None:
        with EPOClient() as client:
            raw = client.fetch_publication(publication_number)
            return raw

    def search_by_publication_date(
        self, publication_date: date, max_results: int = 100
    ) -> Iterator[dict[str, Any]]:
        with EPOClient() as client:
            yield from client.fetch_publications_by_date(publication_date)

    def fetch_full_text(self, publication_number: str) -> dict[str, str | None]:
        with EPOClient() as client:
            return client.fetch_fulltext_for_us_patent(publication_number)

    def fetch_family(self, publication_number: str) -> list[str]:
        try:
            with EPOClient() as client:
                family_data = client.fetch_family(publication_number)
                members = (
                    family_data.get("ops:world-patent-data", {})
                    .get("ops:patent-family", {})
                    .get("family-members", {})
                    .get("family-member", [])
                )
                if isinstance(members, dict):
                    members = [members]
                return [
                    m.get("publication-reference", {}).get("document-id", {}).get("doc-number", {}).get("$", "")
                    for m in members
                ]
        except Exception:
            logger.debug("EPO family fetch failed for %s", publication_number, exc_info=True)
            return []


# Auto-register
try:
    register(EPOOPSProvider.name, EPOOPSProvider())
except Exception:
    logger.warning("EPO OPS provider not registered — credentials may be missing")
