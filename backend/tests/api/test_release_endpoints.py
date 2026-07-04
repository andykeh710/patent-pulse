"""Release-readiness regression tests for the core API surface.

These guard the P0 reported during launch validation: a missing import in a
router (e.g. `Depends` in themes.py) breaks import-time evaluation of route
defaults and takes down the *entire* FastAPI app, so every endpoint returns
500. This suite asserts that the previously-failing endpoints never 500 and
that auth-gated endpoints return 401 (not 500) when logged out.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient


def _cookie(user_id: str = "local-user") -> dict:
    from app.config import settings

    return {
        "auth_session": jwt.encode(
            {
                "sub": user_id,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(days=30),
            },
            settings.auth_secret_key,
            algorithm="HS256",
        )
    }


# Endpoints that should serve a valid payload even with an empty DB and no
# auth (200 with empty/zeroed data — never 500, never a hard auth wall).
PUBLIC_OK_ENDPOINTS = [
    "/api/v1/patents/freshness",
    "/api/v1/patents/stats",
    "/api/v1/today/state",
    "/api/v1/today/highlights",
    "/api/v1/themes",
    "/api/v1/watchlist",
    "/api/v1/opportunity?tab=top&sort=opportunity_score&page_size=5",
    "/api/v1/patents/priority-watch?bucket=expiring_soon&page_size=5",
    "/api/v1/suppliers?sort_by=patent_count&sort_order=desc&min_patent_count=2&page_size=5",
    "/api/v1/suppliers/summary",
    "/api/v1/suppliers/map",
]

# Endpoints that require authentication: 401 when logged out (NOT 500).
AUTH_REQUIRED_ENDPOINTS = [
    "/api/v1/auth/me",
    "/api/v1/suppliers/follows",
]


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize("path", PUBLIC_OK_ENDPOINTS)
async def test_public_endpoint_returns_200_not_500(client: AsyncClient, path: str):
    r = await client.get(path)
    assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:200]}"


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize("path", AUTH_REQUIRED_ENDPOINTS)
async def test_auth_required_endpoint_401_when_logged_out(client: AsyncClient, path: str):
    r = await client.get(path)
    assert r.status_code == 401, f"{path} -> {r.status_code}: {r.text[:200]}"


@pytest.mark.asyncio(loop_scope="function")
async def test_auth_me_returns_user_when_logged_in(client: AsyncClient):
    r = await client.get("/api/v1/auth/me", cookies=_cookie("local-user"))
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "local-user"


@pytest.mark.asyncio(loop_scope="function")
async def test_suppliers_follows_ok_when_logged_in(client: AsyncClient):
    r = await client.get("/api/v1/suppliers/follows", cookies=_cookie("local-user"))
    assert r.status_code == 200
    # Empty state is a valid payload, not an error.
    assert isinstance(r.json(), list)


@pytest.mark.asyncio(loop_scope="function")
async def test_themes_endpoint_lists_seeded_system_themes(client: AsyncClient):
    """System themes are DB-seeded (conftest seeds 3). Confirms /themes serves
    them as real records rather than relying on frontend-hardcoded data."""
    r = await client.get("/api/v1/themes")
    assert r.status_code == 200
    themes = r.json()
    assert isinstance(themes, list)
    assert len(themes) >= 3
