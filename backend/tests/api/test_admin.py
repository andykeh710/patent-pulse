"""Tests for admin endpoints (Sprint 7)."""
import pytest


def _cookie(user_id="local-user"):
    from datetime import datetime, timedelta, timezone

    import jwt

    from app.config import settings
    return {"auth_session": jwt.encode(
        {"sub": user_id, "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(days=30)},
        settings.auth_secret_key, algorithm="HS256",
    )}


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_users_unauthorized(client, db_session):
    r = await client.get("/api/v1/admin/users")
    assert r.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_non_admin_gets_403(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = False
    await db_session.commit()
    r = await client.get("/api/v1/admin/users", cookies=_cookie())
    assert r.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_lists_users(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = True
    await db_session.commit()
    r = await client.get("/api/v1/admin/users", cookies=_cookie())
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert any(u["id"] == "local-user" for u in data["users"])


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_overrides_tier(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User
    from app.core.billing_models import BillingSubscription
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = True
    await db_session.commit()

    r = await client.post("/api/v1/admin/users/local-user/tier", json={"tier": "lifetime"}, cookies=_cookie())
    assert r.status_code == 200
    assert r.json()["tier"] == "lifetime"

    await db_session.refresh(user)
    assert user.tier == "lifetime"

    billing = (await db_session.execute(
        select(BillingSubscription).where(BillingSubscription.user_id == "local-user")
    )).scalar_one_or_none()
    assert billing is not None
    assert billing.tier == "lifetime"


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_override_invalid_tier_422(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = True
    await db_session.commit()
    r = await client.post("/api/v1/admin/users/local-user/tier", json={"tier": "platinum"}, cookies=_cookie())
    assert r.status_code == 422


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_lists_exports(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User
    from app.core.billing_models import Export
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.is_admin = True
    await db_session.commit()

    db_session.add(Export(user_id="local-user", export_type="csv", scope="expiry_list"))
    await db_session.commit()

    r = await client.get("/api/v1/admin/exports", cookies=_cookie())
    assert r.status_code == 200
    assert len(r.json()) >= 1
