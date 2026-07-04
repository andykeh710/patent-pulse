"""
ScrapeGraphAI provider — DISABLED IN V1.

Planned Enterprise-tier-gated activation in V1.1 for targeted extraction.
See .hermes/plans/2026-05-30_global-patent-data-acquisition-sprint.md for context.

Credit cost is not sustainable for Free/Basic/Lifetime tiers ($200+ for
WIPO backfill alone). Deferred to Enterprise-only V1.1 once we have
paying customers and can measure ROI.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import date
from typing import Any

from app.config import settings
from app.patent_sources.base import BasePatentProvider

logger = logging.getLogger(__name__)


class ScrapeGraphProvider(BasePatentProvider):
    """ScrapeGraphAI extraction provider — disabled in V1."""

    name = "scrapegraph"

    def __init__(self):
        self._api_key = getattr(settings, "scrapegraph_api_key", None) or ""
        self._enabled = str(getattr(settings, "scrapegraph_enabled", False)).lower() in (
            "true",
            "1",
            "yes",
        )

    @property
    def enabled(self) -> bool:
        return self._enabled and bool(self._api_key)

    def _check_enabled(self) -> bool:
        if not self._enabled:
            logger.info("ScrapeGraphAI disabled by config")
            return False
        if not self._api_key:
            logger.info("ScrapeGraphAI disabled — no API key set")
            return False
        return True

    def fetch_by_publication_number(self, publication_number: str) -> dict[str, Any] | None:
        if not self._check_enabled():
            return None
        return None

    def search_by_publication_date(
        self, publication_date: date, max_results: int = 100
    ) -> Iterator[dict[str, Any]]:
        if not self._check_enabled():
            return
        return
        yield


# NOT auto-registered in V1 — see registry comments.
# To enable in V1.1, add ScrapeGraphProvider to import_providers().
