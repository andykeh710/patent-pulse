"""Tests for admin endpoints (Sprint 7 + Sprint 1.5 gate)."""

import pytest


def _cookie(user_id="local-user"):
    from datetime import datetime, timedelta, timezone

    import jwt

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


async def _make_admin(db_session) -> None:
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = True
    await db_session.commit()


async def _make_non_admin(db_session) -> None:
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = False
    await db_session.commit()


# -- Trigger endpoint auth tests (Sprint 1.5 gate) --

TRIGGER_ENDPOINTS = [
    "/api/v1/admin/trigger-ingest",
    "/api/v1/admin/trigger-summarize",
    "/api/v1/admin/trigger-family-resolution",
    "/api/v1/admin/trigger-expiry-backfill",
    "/api/v1/admin/trigger-enrich-abstracts",
    "/api/v1/admin/trigger-resummarize",
    "/api/v1/admin/trigger-match-themes",
    "/api/v1/admin/trigger-assignee-backfill",
]


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize("path", TRIGGER_ENDPOINTS)
async def test_trigger_unauthorized_no_cookie(client, db_session, path):
    """Trigger endpoints must reject requests without auth cookies."""
    r = await client.post(path)
    assert r.status_code in (401, 403), f"{path}: expected 401/403, got {r.status_code}"


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize("path", TRIGGER_ENDPOINTS)
async def test_trigger_forbidden_non_admin(client, db_session, path):
    """Trigger endpoints must reject non-admin users."""
    await _make_non_admin(db_session)
    r = await client.post(path, cookies=_cookie())
    assert r.status_code in (
        401,
        403,
    ), f"{path}: expected 401/403 for non-admin, got {r.status_code}"


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.xfail(reason="KI-005: Trigger endpoint missing — returns 404")
async def test_trigger_assignee_backfill_admin_accepted(client, db_session):
    """Trigger assignee backfill accepts admin user."""
    await _make_admin(db_session)
    r = await client.post("/api/v1/admin/trigger-assignee-backfill", cookies=_cookie())
    assert r.status_code == 200, f"expected 200 for admin, got {r.status_code}"
    data = r.json()
    assert "task_id" in data
    assert data["status"] == "enqueued"


# -- Existing admin tests --


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_users_unauthorized(client, db_session):
    r = await client.get("/api/v1/admin/users")
    assert r.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_non_admin_gets_403(client, db_session):
    await _make_non_admin(db_session)
    r = await client.get("/api/v1/admin/users", cookies=_cookie())
    assert r.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_lists_users(client, db_session):
    await _make_admin(db_session)
    r = await client.get("/api/v1/admin/users", cookies=_cookie())
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert any(u["id"] == "local-user" for u in data["users"])


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_overrides_tier(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = True
    await db_session.commit()

    r = await client.post(
        "/api/v1/admin/users/local-user/tier", json={"tier": "lifetime"}, cookies=_cookie()
    )
    assert r.status_code == 200
    data = r.json()
    assert data["tier"] == "lifetime"


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_system_health(client, db_session):
    await _make_admin(db_session)
    r = await client.get("/api/v1/admin/system-health", cookies=_cookie())
    assert r.status_code == 200
