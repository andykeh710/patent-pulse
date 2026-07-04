"""Tests for API key management (Sprint 7)."""

import pytest


def _make_cookie(user_id="local-user"):
    from datetime import datetime, timedelta, timezone

    import jwt

    from app.config import settings

    return jwt.encode(
        {
            "sub": user_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
        },
        settings.auth_secret_key,
        algorithm="HS256",
    )


def _auth(client, user_id="local-user"):
    client.cookies.set("auth_session", _make_cookie(user_id))


@pytest.mark.asyncio(loop_scope="function")
async def test_free_user_post_gets_402(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "free"
    await db_session.commit()
    _auth(client)
    r = await client.post("/api/v1/account/api-keys", json={})
    assert r.status_code == 402


@pytest.mark.asyncio(loop_scope="function")
async def test_enterprise_user_creates_key(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "enterprise"
    await db_session.commit()
    _auth(client)
    r = await client.post("/api/v1/account/api-keys", json={"name": "Test Key"})
    assert r.status_code == 200
    data = r.json()
    assert data["raw_token"].startswith("pp_live_")
    assert len(data["raw_token"]) > 40


@pytest.mark.asyncio(loop_scope="function")
async def test_list_does_not_expose_raw_token(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "enterprise"
    await db_session.commit()
    _auth(client)

    await client.post("/api/v1/account/api-keys", json={"name": "K1"})
    r = await client.get("/api/v1/account/api-keys")
    assert r.status_code == 200
    for k in r.json():
        assert "raw_token" not in k or k["raw_token"] is None


@pytest.mark.asyncio(loop_scope="function")
async def test_ownership_isolation(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "enterprise"
    await db_session.commit()
    _auth(client)
    r = await client.post("/api/v1/account/api-keys", json={})
    key_id = r.json()["id"]

    # Other user tries to delete
    _auth(client, "local-user-2")
    r = await client.delete(f"/api/v1/account/api-keys/{key_id}")
    assert r.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_own_key_returns_204(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "enterprise"
    await db_session.commit()
    _auth(client)
    r = await client.post("/api/v1/account/api-keys", json={})
    key_id = r.json()["id"]

    r = await client.delete(f"/api/v1/account/api-keys/{key_id}")
    assert r.status_code == 204


@pytest.mark.asyncio(loop_scope="function")
async def test_revoked_key_cannot_auth(client, db_session):
    from sqlalchemy import select

    from app.auth.api_keys import authenticate_api_key
    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "enterprise"
    await db_session.commit()
    _auth(client)

    r = await client.post("/api/v1/account/api-keys", json={})
    raw = r.json()["raw_token"]
    key_id = r.json()["id"]

    assert await authenticate_api_key(db_session, raw) is not None

    await client.delete(f"/api/v1/account/api-keys/{key_id}")
    assert await authenticate_api_key(db_session, raw) is None


@pytest.mark.asyncio(loop_scope="function")
async def test_bearer_token_auth_via_api(client, db_session):
    """API key can authenticate via authenticate_api_key."""
    from sqlalchemy import select

    from app.auth.api_keys import authenticate_api_key
    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "enterprise"
    await db_session.commit()
    _auth(client)

    r = await client.post("/api/v1/account/api-keys", json={})
    raw = r.json()["raw_token"]

    authed_user = await authenticate_api_key(db_session, raw)
    assert authed_user is not None
    assert authed_user.id == "local-user"
