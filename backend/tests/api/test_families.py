from datetime import date

import pytest
from httpx import AsyncClient

from app.core.models import PatentPublication


@pytest.mark.asyncio
async def test_get_family_handles_missing_publication_dates(
    client: AsyncClient, db_session
) -> None:
    family_id = "FAM-MIXED-DATES"
    patents = [
        PatentPublication(
            doc_id="USPTO:FAM001",
            family_id=family_id,
            office="USPTO",
            publication_number="FAM001",
            legal_status="PUBLISHED",
            publication_date=None,
        ),
        PatentPublication(
            doc_id="EPO:FAM002",
            family_id=family_id,
            office="EPO",
            publication_number="FAM002",
            legal_status="PUBLISHED",
            publication_date=date(2024, 1, 15),
        ),
    ]
    for patent in patents:
        db_session.add(patent)
    await db_session.commit()

    response = await client.get(f"/api/v1/families/{family_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["primary"]["doc_id"] == "EPO:FAM002"
    assert data["member_count"] == 2
