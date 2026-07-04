"""
Dev fixture loader.

Provides a pytest fixture ``dev_fixture`` that reads
``tests/fixtures/dev_50.json`` and inserts the patents into the active
test session.

Tests opt in via::

    @pytest.mark.dev_fixture
    async def test_foo(dev_fixture, client):
        ...

The fixture file is intentionally pre-populated with patents that have
``summary`` fields so the AI cache-hit path can be exercised.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import PatentPublication

FIXTURE_PATH = Path(__file__).parent / "dev_50.json"


def _coerce_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def load_fixture() -> dict[str, Any]:
    """Load the dev fixture JSON. Raises if the file is missing."""
    if not FIXTURE_PATH.exists():
        raise FileNotFoundError(f"dev fixture not found at {FIXTURE_PATH}")
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


async def insert_dev_fixture(session: AsyncSession) -> int:
    """Insert all dev fixture patents into the given async session.

    Returns the number of patents inserted. Idempotent within a single
    transaction.
    """
    data = load_fixture()
    inserted = 0
    for raw in data.get("patents", []):
        patent = PatentPublication(
            id=UUID(raw["id"]) if "id" in raw else None,
            doc_id=raw["doc_id"],
            office=raw.get("office", "USPTO"),
            publication_number=raw.get("publication_number", raw["doc_id"]),
            application_number=raw.get("application_number"),
            kind_code=raw.get("kind_code"),
            family_id=raw.get("family_id"),
            filing_date=_coerce_date(raw.get("filing_date")),
            priority_date=_coerce_date(raw.get("priority_date")),
            publication_date=_coerce_date(raw.get("publication_date")),
            grant_date=_coerce_date(raw.get("grant_date")),
            assignees=raw.get("assignees") or [],
            inventors=raw.get("inventors") or [],
            cpc=raw.get("cpc") or [],
            ipc=raw.get("ipc") or [],
            title=raw.get("title"),
            abstract=raw.get("abstract"),
            claims_text=raw.get("claims_text"),
            description_text=raw.get("description_text"),
            citations_backward=raw.get("citations_backward") or [],
            family_members=raw.get("family_members") or [],
            legal_status=raw.get("legal_status"),
            maintenance_status=raw.get("maintenance_status"),
            estimated_expiry_date=_coerce_date(raw.get("estimated_expiry_date")),
            summary=raw.get("summary"),
            novel_applications=raw.get("novel_applications") or [],
            interesting_score=raw.get("interesting_score"),
            score_breakdown=raw.get("score_breakdown"),
            tags=raw.get("tags"),
            opportunity_score=raw.get("opportunity_score"),
            opportunity_breakdown=raw.get("opportunity_breakdown"),
            why_now_text=raw.get("why_now_text"),
            summarized_at=_coerce_datetime(raw.get("summarized_at")),
        )
        session.add(patent)
        inserted += 1
    await session.flush()
    return inserted
