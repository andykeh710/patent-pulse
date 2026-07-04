"""
Abstract base class for patent data providers.

Every provider (EPO OPS, WIPO, Google Patents, ScrapeGraph) implements
this interface. Methods return None or raise on failure; callers handle
fallback chaining.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import date
from typing import Any


class BasePatentProvider(ABC):
    """Interface for patent data acquisition sources."""

    name: str = "base"

    @abstractmethod
    def fetch_by_publication_number(self, publication_number: str) -> dict[str, Any] | None:
        """Fetch bibliographic data for a single publication by number."""
        ...

    @abstractmethod
    def search_by_publication_date(
        self, publication_date: date, max_results: int = 100
    ) -> Iterator[dict[str, Any]]:
        """Search for publications by date. Yields raw records."""
        ...

    def fetch_full_text(self, publication_number: str) -> dict[str, str | None]:
        """Fetch abstract and claims for a publication.

        Returns dict with 'abstract' and 'claims_text' keys. Values may be None.
        """
        return {"abstract": None, "claims_text": None}

    def fetch_images(self, publication_number: str) -> list[dict[str, Any]]:
        """Fetch available images/figures for a publication.

        Returns list of dicts with: source_url, page_number, figure_label,
        mime_type, width, height.
        """
        return []

    def fetch_family(self, publication_number: str) -> list[str]:
        """Fetch family member publication numbers."""
        return []

    def fetch_citations(self, publication_number: str) -> dict[str, list[str]]:
        """Fetch forward and backward citations.

        Returns dict with 'forward' and 'backward' lists of doc IDs.
        """
        return {"forward": [], "backward": []}
