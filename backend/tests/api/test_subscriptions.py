"""Tests for subscription API endpoints."""
import hashlib
import hmac
from uuid import uuid4

import pytest

SECRET = "test-secret-key-for-tests"


@pytest.fixture(autouse=True)
def _set_secret(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET_KEY", SECRET)


@pytest.fixture(autouse=True, scope="session")
def _patch_settings():
    """Ensure the global settings object has auth_secret_key for API tests."""
    from app.config import settings as global_settings
    global_settings.auth_secret_key = SECRET
    global_settings.resend_api_key = "re_test"
    global_settings.email_from_address = "test@example.com"
    global_settings.email_dev_recipient = "dev@example.com"


@pytest.mark.asyncio(loop_scope="function")
async def test_get_subscriptions_no_cookie_returns_401(client):
    r = await client.get("/api/v1/subscriptions")
    assert r.status_code == 401


def _make_session_cookie(user_id="local-user"):
    from datetime import datetime, timedelta, timezone

    import jwt
    token = jwt.encode(
        {"sub": user_id, "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(days=30)},
        SECRET, algorithm="HS256",
    )
    return {"auth_session": token}


@pytest.mark.asyncio(loop_scope="function")
async def test_create_subscription(client, db_session):
    from sqlalchemy import select

    from app.core.theme_models import Theme
    themes = (await db_session.execute(select(Theme).limit(1))).scalars().all()
    if not themes:
        pytest.skip("No themes seeded")
    tid = str(themes[0].id)

    r = await client.post("/api/v1/subscriptions", json={"theme_id": tid, "mode": "weekly_digest"}, cookies=_make_session_cookie())
    assert r.status_code == 201, r.text
    assert r.json()["mode"] == "weekly_digest"


@pytest.mark.asyncio(loop_scope="function")
async def test_duplicate_subscription_returns_409(client, db_session):
    from sqlalchemy import select

    from app.core.theme_models import Theme
    themes = (await db_session.execute(select(Theme).limit(1))).scalars().all()
    if not themes:
        pytest.skip("No themes seeded")
    tid = str(themes[0].id)
    cookie = _make_session_cookie()

    r1 = await client.post("/api/v1/subscriptions", json={"theme_id": tid, "mode": "instant_alert"}, cookies=cookie)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/subscriptions", json={"theme_id": tid, "mode": "instant_alert"}, cookies=cookie)
    assert r2.status_code == 409


@pytest.mark.asyncio(loop_scope="function")
async def test_patch_own_subscription(client, db_session):
    from sqlalchemy import select

    from app.core.theme_models import Theme
    themes = (await db_session.execute(select(Theme).limit(1))).scalars().all()
    if not themes:
        pytest.skip("No themes seeded")
    tid = str(themes[0].id)
    cookie = _make_session_cookie()

    r1 = await client.post("/api/v1/subscriptions", json={"theme_id": tid, "mode": "weekly_digest"}, cookies=cookie)
    sub_id = r1.json()["id"]

    r2 = await client.patch(f"/api/v1/subscriptions/{sub_id}", json={"paused": True}, cookies=cookie)
    assert r2.status_code == 200
    assert r2.json()["paused"] is True


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_own_subscription(client, db_session):
    from sqlalchemy import select

    from app.core.theme_models import Theme
    themes = (await db_session.execute(select(Theme).limit(1))).scalars().all()
    if not themes:
        pytest.skip("No themes seeded")
    tid = str(themes[0].id)
    cookie = _make_session_cookie()

    r1 = await client.post("/api/v1/subscriptions", json={"theme_id": tid, "mode": "weekly_digest"}, cookies=cookie)
    sub_id = r1.json()["id"]

    r2 = await client.delete(f"/api/v1/subscriptions/{sub_id}", cookies=cookie)
    assert r2.status_code == 204


def _sign(id_str):
    return hmac.new(SECRET.encode(), id_str.encode(), hashlib.sha256).hexdigest()


@pytest.mark.asyncio(loop_scope="function")
async def test_unsubscribe_with_valid_token_pauses(client, db_session):
    from sqlalchemy import select

    from app.core.theme_models import Theme
    themes = (await db_session.execute(select(Theme).limit(1))).scalars().all()
    if not themes:
        pytest.skip("No themes seeded")
    tid = str(themes[0].id)
    cookie = _make_session_cookie()

    r1 = await client.post("/api/v1/subscriptions", json={"theme_id": tid, "mode": "weekly_digest"}, cookies=cookie)
    sub_id = r1.json()["id"]
    token = _sign(sub_id)

    r2 = await client.get(f"/api/v1/subscriptions/unsubscribe?subscription={sub_id}&token={token}")
    assert r2.status_code == 200
    assert r2.json()["ok"] is True


@pytest.mark.asyncio(loop_scope="function")
async def test_unsubscribe_bad_token_returns_400(client):
    r = await client.get(f"/api/v1/subscriptions/unsubscribe?subscription={uuid4()}&token=bad")
    assert r.status_code == 400
