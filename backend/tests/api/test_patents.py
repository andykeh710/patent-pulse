import uuid
from datetime import date

import pytest
from httpx import AsyncClient

from app.core.models import PatentPublication


@pytest.mark.asyncio
async def test_list_patents_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/patents")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_patents_with_data(client: AsyncClient, db_session) -> None:
    patent = PatentPublication(
        doc_id="USPTO:TEST001",
        office="USPTO",
        publication_number="TEST001",
        title="Test Patent",
        abstract="Test abstract",
        legal_status="GRANTED",
        publication_date=date(2024, 1, 15),
    )
    db_session.add(patent)
    await db_session.commit()

    response = await client.get("/api/v1/patents")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["doc_id"] == "USPTO:TEST001"


@pytest.mark.asyncio
async def test_list_patents_filter_by_office(client: AsyncClient, db_session) -> None:
    patents = [
        PatentPublication(
            doc_id="USPTO:US001",
            office="USPTO",
            publication_number="US001",
            title="US Patent",
        ),
        PatentPublication(
            doc_id="EPO:EP001",
            office="EPO",
            publication_number="EP001",
            title="EP Patent",
        ),
    ]
    for p in patents:
        db_session.add(p)
    await db_session.commit()

    response = await client.get("/api/v1/patents?office=USPTO")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["doc_id"] == "USPTO:US001"


@pytest.mark.asyncio
async def test_list_patents_pagination(client: AsyncClient, db_session) -> None:
    for i in range(25):
        patent = PatentPublication(
            doc_id=f"USPTO:PAG{i:03d}",
            office="USPTO",
            publication_number=f"PAG{i:03d}",
            title=f"Patent {i}",
        )
        db_session.add(patent)
    await db_session.commit()

    response = await client.get("/api/v1/patents?page=1&page_size=10")
    data = response.json()
    assert data["total"] == 25
    assert len(data["items"]) == 10
    assert data["page"] == 1
    assert data["pages"] == 3

    response = await client.get("/api/v1/patents?page=3&page_size=10")
    data = response.json()
    assert len(data["items"]) == 5


@pytest.mark.asyncio
async def test_list_patents_sort_by_opportunity_score(
    client: AsyncClient, db_session
) -> None:
    patents = [
        PatentPublication(
            doc_id="USPTO:OPPLOW",
            office="USPTO",
            publication_number="OPPLOW",
            title="Low opportunity",
            opportunity_score=15,
        ),
        PatentPublication(
            doc_id="USPTO:OPPHIGH",
            office="USPTO",
            publication_number="OPPHIGH",
            title="High opportunity",
            opportunity_score=90,
        ),
    ]
    for patent in patents:
        db_session.add(patent)
    await db_session.commit()

    response = await client.get(
        "/api/v1/patents?sort_by=opportunity_score&sort_order=desc"
    )

    assert response.status_code == 200
    data = response.json()
    assert [item["doc_id"] for item in data["items"]] == [
        "USPTO:OPPHIGH",
        "USPTO:OPPLOW",
    ]


@pytest.mark.asyncio
async def test_get_patent_by_id(client: AsyncClient, db_session) -> None:
    patent = PatentPublication(
        doc_id="USPTO:DETAIL001",
        office="USPTO",
        publication_number="DETAIL001",
        title="Detail Test Patent",
        abstract="Test abstract for detail",
        assignees=["Test Corp"],
        inventors=["John Doe"],
        cpc=["G06F 21/00"],
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    response = await client.get(f"/api/v1/patents/{patent.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["doc_id"] == "USPTO:DETAIL001"
    assert data["title"] == "Detail Test Patent"
    assert "Test Corp" in data["assignees"]


@pytest.mark.asyncio
async def test_get_patent_not_found(client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/patents/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_patent_summary(client: AsyncClient, db_session) -> None:
    from datetime import datetime

    summary = {
        "what_it_is": "A test invention",
        "problem_solved": "Test problem",
        "how_it_works": "Test mechanism",
        "commercial_significance": "Test significance",
        "who_should_care": ["Engineers"],
        "novel_applications": [],
        "confidence_note": "High",
        "source_spans": [],
    }
    patent = PatentPublication(
        doc_id="USPTO:SUM001",
        office="USPTO",
        publication_number="SUM001",
        title="Summary Test",
        summary=summary,
        summarized_at=datetime.utcnow(),
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    response = await client.get(f"/api/v1/patents/{patent.id}/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["what_it_is"] == "A test invention"


@pytest.mark.asyncio
async def test_get_patent_summary_not_yet_summarized(
    client: AsyncClient, db_session
) -> None:
    patent = PatentPublication(
        doc_id="USPTO:NOSUM001",
        office="USPTO",
        publication_number="NOSUM001",
        title="No Summary Test",
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)

    response = await client.get(f"/api/v1/patents/{patent.id}/summary")
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_get_stats(client: AsyncClient, db_session) -> None:
    patents = [
        PatentPublication(
            doc_id="USPTO:STAT001",
            office="USPTO",
            publication_number="STAT001",
            legal_status="GRANTED",
        ),
        PatentPublication(
            doc_id="USPTO:STAT002",
            office="USPTO",
            publication_number="STAT002",
            legal_status="PUBLISHED",
        ),
    ]
    for p in patents:
        db_session.add(p)
    await db_session.commit()

    response = await client.get("/api/v1/patents/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_patents"] == 2
    assert data["total_grants"] == 1
    assert data["total_applications"] == 1
