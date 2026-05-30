"""
Provider registry.

Maps provider names to provider instances. Used by the data-health
dashboard and task runners to chain providers for fallback.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.patent_sources.base import BasePatentProvider

logger = logging.getLogger(__name__)

_registry: dict[str, "BasePatentProvider"] = {}


def register(name: str, provider: "BasePatentProvider") -> None:
    """Register a provider by name."""
    _registry[name] = provider
    logger.info("Registered patent provider: %s", name)


def get(name: str) -> "BasePatentProvider | None":
    """Get a registered provider by name."""
    return _registry.get(name)


def list_all() -> list[str]:
    """List all registered provider names."""
    return sorted(_registry.keys())


def import_providers() -> None:
    """Import and register all known providers.

    Called once at startup. Each provider module registers itself on import.

    NOTE: ScrapeGraphAI is disabled in V1 (Enterprise-tier-gated V1.1).
    It is NOT imported here — see scrapegraph_provider.py for details.
    """
    from app.patent_sources import (  # noqa: F401
        epo_ops_provider,
        google_patents_provider,
        wipo_provider,
        wipo_bigquery_provider,
        # scrapegraph_provider,  # V1.1: Enterprise-tier-gated
    )
