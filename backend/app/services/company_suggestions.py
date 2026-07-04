"""Company suggestion logic — persona-biased company recommendations."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_PERSONA_COMPANIES = {
    "operator": [
        "SAMSUNG ELECTRONICS CO LTD",
        "TOYOTA JIDOSHA KABUSHIKI KAISHA",
        "BOE TECHNOLOGY GROUP CO LTD",
        "HYUNDAI MOTOR CO",
        "LG ELECTRONICS INC",
        "HUAWEI TECHNOLOGIES CO LTD",
    ],
    "investor": [
        "APPLE INC",
        "NVIDIA CORP",
        "MICROSOFT CORP",
        "ALPHABET INC",
        "META PLATFORMS INC",
        "TESLA INC",
        "SAMSUNG ELECTRONICS CO LTD",
    ],
    "curious": [
        "SAMSUNG ELECTRONICS CO LTD",
        "APPLE INC",
        "BOE TECHNOLOGY GROUP CO LTD",
        "TOYOTA JIDOSHA KABUSHIKI KAISHA",
        "IBM CORP",
        "INTEL CORP",
        "NVIDIA CORP",
        "CANON KK",
    ],
}


async def get_suggested_companies(
    db: AsyncSession,
    persona: str = "curious",
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Return persona-biased company suggestions with patent counts."""
    candidates = _PERSONA_COMPANIES.get(persona, _PERSONA_COMPANIES["curious"])

    result: list[dict[str, Any]] = []
    for company_name in candidates:
        row = await db.execute(
            text(
                "SELECT COUNT(*) as total FROM patent_publications "
                "WHERE assignees IS NOT NULL AND assignees->>0 = :name"
            ),
            {"name": company_name},
        )
        total = row.scalar() or 0

        row = await db.execute(
            text(
                "SELECT COUNT(*) as recent FROM patent_publications "
                "WHERE assignees IS NOT NULL AND assignees->>0 = :name "
                "AND publication_date >= CURRENT_DATE - INTERVAL '12 months'"
            ),
            {"name": company_name},
        )
        recent = row.scalar() or 0

        result.append(
            {
                "name": company_name,
                "patent_count": total,
                "last_12mo_count": recent,
            }
        )

    result.sort(key=lambda c: c["patent_count"], reverse=True)
    return result[:limit]
