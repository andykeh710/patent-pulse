import pytest
from httpx import AsyncClient

from app.core.models import PatentPublication


@pytest.mark.asyncio
async def test_search_patents_empty_db(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_search_requires_query(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_min_query_length(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=ab")
    assert response.status_code == 422
