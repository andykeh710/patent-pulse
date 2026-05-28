"""
Tests for PR12 API-layer rate limiting (slowapi).

The limiter uses in-process storage (``memory://``), so tests must
reset it between runs to avoid cross-test contamination.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.middleware.rate_limit import limiter


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Flush slowapi in-memory storage before every test."""
    limiter.reset()
    yield


@pytest.mark.asyncio
async def test_health_endpoint_exempt(client: AsyncClient):
    """Hit /health several times — must never 429 (exempt from rate limiting)."""
    for _ in range(10):
        resp = await client.get("/health")
        assert resp.status_code == 200, f"got {resp.status_code}"


@pytest.mark.asyncio
async def test_auth_verify_exempt(client: AsyncClient):
    """Hit /api/v1/auth/verify 80 times — must never 429 (exempt).

    Uses a bad token so the endpoint returns 400, not 429.
    """
    for _ in range(80):
        resp = await client.get("/api/v1/auth/verify?token=bad")
        assert resp.status_code != 429, f"got 429 on exempt endpoint"


@pytest.mark.asyncio
async def test_default_limit_60_per_minute(client: AsyncClient):
    """60 requests → all 200.  61st → 429."""
    for i in range(60):
        resp = await client.get("/")
        assert resp.status_code == 200, f"request {i + 1} got {resp.status_code}"

    resp = await client.get("/")
    assert resp.status_code == 429, f"expected 429, got {resp.status_code}"


@pytest.mark.asyncio
async def test_429_response_is_json_with_error_key(client: AsyncClient):
    """The 429 response body is JSON with an 'error' key."""
    for _ in range(60):
        await client.get("/")

    resp = await client.get("/")
    assert resp.status_code == 429
    body = resp.json()
    assert "error" in body, f"missing error key in {body}"
    assert "60 per 1 minute" in body["error"]
