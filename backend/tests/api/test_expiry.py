from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.core.models import PatentPublication


@pytest.mark.asyncio
async def test_list_expiring_patents_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/expiry")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_expiring_patents(client: AsyncClient, db_session) -> None:
    today = date.today()
    patents = [
        PatentPublication(
            doc_id="USPTO:EXP001",
            office="USPTO",
            publication_number="EXP001",
            title="Expiring Soon",
            legal_status="GRANTED",
            estimated_expiry_date=today + timedelta(days=30),
        ),
        PatentPublication(
            doc_id="USPTO:EXP002",
            office="USPTO",
            publication_number="EXP002",
            title="Expiring Later",
            legal_status="GRANTED",
            estimated_expiry_date=today + timedelta(days=500),
        ),
        PatentPublication(
            doc_id="USPTO:EXP003",
            office="USPTO",
            publication_number="EXP003",
            title="Already Expired",
            legal_status="GRANTED",
            estimated_expiry_date=today - timedelta(days=30),
        ),
    ]
    for p in patents:
        db_session.add(p)
    await db_session.commit()

    response = await client.get("/api/v1/expiry?days_ahead=365")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["doc_id"] == "USPTO:EXP001"
    assert data["items"][0]["days_until_expiry"] == 30


@pytest.mark.asyncio
async def test_expiry_filter_by_days(client: AsyncClient, db_session) -> None:
    today = date.today()
    patent = PatentPublication(
        doc_id="USPTO:EXPDAYS001",
        office="USPTO",
        publication_number="EXPDAYS001",
        legal_status="GRANTED",
        estimated_expiry_date=today + timedelta(days=100),
    )
    db_session.add(patent)
    await db_session.commit()

    response = await client.get("/api/v1/expiry?days_ahead=90")
    assert response.json()["total"] == 0

    response = await client.get("/api/v1/expiry?days_ahead=180")
    assert response.json()["total"] == 1
