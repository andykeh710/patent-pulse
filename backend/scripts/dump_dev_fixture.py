"""Dump a stratified 50-patent dev fixture from the live DB.

Writes to ``tests/fixtures/dev_50.json``. Stratifies across 6 CPC
sections (A, B, C, G, H, F) and prefers patents with ``summary`` set so
AI-cache regression tests exercise the cache-hit path.

Usage::

    python -m scripts.dump_dev_fixture
    python -m scripts.dump_dev_fixture --size 50 --sections A B C G H F
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.models import PatentPublication
from app.database import async_session_maker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("dump_dev_fixture")

OUT_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "dev_50.json"
DEFAULT_SECTIONS = ["A", "B", "C", "G", "H", "F"]


def _serialize(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _to_dict(p: PatentPublication) -> dict[str, Any]:
    fields = [
        "doc_id",
        "office",
        "publication_number",
        "application_number",
        "kind_code",
        "family_id",
        "filing_date",
        "priority_date",
        "publication_date",
        "grant_date",
        "assignees",
        "inventors",
        "cpc",
        "ipc",
        "title",
        "abstract",
        "claims_text",
        "description_text",
        "citations_backward",
        "family_members",
        "legal_status",
        "maintenance_status",
        "estimated_expiry_date",
        "summary",
        "novel_applications",
        "interesting_score",
        "score_breakdown",
        "tags",
        "opportunity_score",
        "opportunity_breakdown",
        "why_now_text",
        "summarized_at",
    ]
    out: dict[str, Any] = {"id": str(p.id)}
    for f in fields:
        out[f] = _serialize(getattr(p, f, None))
    return out


async def _pick_for_section(
    section: str, per: int, prefer_summary: bool
) -> list[PatentPublication]:
    async with async_session_maker() as session:
        stmt = (
            select(PatentPublication)
            .where(PatentPublication.cpc.cast_to(None) is not None)
            .where(PatentPublication.title.isnot(None))
        )
        # Filter on cpc array containing any string starting with section.
        from sqlalchemy import text

        stmt = (
            select(PatentPublication)
            .where(
                text(
                    "EXISTS (SELECT 1 FROM jsonb_array_elements_text(cpc) elem "
                    "WHERE elem LIKE :prefix)"
                ).bindparams(prefix=f"{section}%")
            )
            .where(PatentPublication.title.isnot(None))
        )
        if prefer_summary:
            stmt = stmt.order_by(
                PatentPublication.summary.is_(None),
                PatentPublication.grant_date.desc().nullslast(),
            )
        else:
            stmt = stmt.order_by(PatentPublication.grant_date.desc().nullslast())
        stmt = stmt.limit(per)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def _dump(size: int, sections: list[str]) -> dict[str, Any]:
    per = max(1, size // len(sections))
    picked: list[PatentPublication] = []
    for sect in sections:
        rows = await _pick_for_section(sect, per, prefer_summary=True)
        logger.info("section %s -> %d patents", sect, len(rows))
        picked.extend(rows)
    # Trim or pad
    picked = picked[:size]

    return {
        "_meta": {
            "description": "Deterministic dev fixture for AI tests.",
            "stratification": f"sections={sections}, per={per}, prefer_summary=true",
            "schema_version": 1,
            "generated_at": datetime.utcnow().isoformat(),
        },
        "patents": [_to_dict(p) for p in picked],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=50)
    parser.add_argument("--sections", nargs="+", default=DEFAULT_SECTIONS)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    data = asyncio.run(_dump(args.size, args.sections))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    logger.info("wrote %d patents to %s", len(data["patents"]), args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
