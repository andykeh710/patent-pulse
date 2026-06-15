"""Tests for Sprint 3 today/state and today/mark-seen endpoints."""
import pytest
from httpx import AsyncClient


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


# -- GET /today/state --


@pytest.mark.asyncio(loop_scope="function")
async def test_today_state_first_time_user_no_cookie(client: AsyncClient):
    """Without auth, returns welcome label but no last_seen_at."""
    r = await client.get("/api/v1/today/state")
    assert r.status_code == 200
    data = r.json()
    assert data["last_seen_at"] is None
    assert "generated_at" in data
    assert data["comparison_label"] == "Welcome — your first Today briefing"


@pytest.mark.asyncio(loop_scope="function")
async def test_today_state_first_time_with_cookie_no_history(client: AsyncClient, db_session):
    """Authenticated first-time user: last_seen_at is None."""
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.last_today_seen_at = None
    user.previous_today_seen_at = None
    await db_session.commit()

    r = await client.get("/api/v1/today/state", cookies=_cookie("local-user"))
    assert r.status_code == 200
    data = r.json()
    assert data["last_seen_at"] is None
    assert "Welcome" in data["comparison_label"]


@pytest.mark.asyncio(loop_scope="function")
async def test_today_state_returning_user(client: AsyncClient, db_session):
    """Returning user gets last_seen_at and a comparison label."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.core.ai_models import User

    three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.last_today_seen_at = three_days_ago
    user.previous_today_seen_at = None
    await db_session.commit()

    r = await client.get("/api/v1/today/state", cookies=_cookie("local-user"))
    assert r.status_code == 200
    data = r.json()
    assert data["last_seen_at"] is not None
    # Comparison label should mention the date (3 days ago)
    assert three_days_ago.strftime("%b %d, %Y") in data["comparison_label"]


@pytest.mark.asyncio(loop_scope="function")
async def test_today_state_returning_same_day(client: AsyncClient, db_session):
    """Returning same day shows 'Since earlier today'."""
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.core.ai_models import User

    now = datetime.now(timezone.utc)
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.last_today_seen_at = now
    user.previous_today_seen_at = None
    await db_session.commit()

    r = await client.get("/api/v1/today/state", cookies=_cookie("local-user"))
    assert r.status_code == 200
    data = r.json()
    assert "earlier today" in data["comparison_label"]


@pytest.mark.asyncio(loop_scope="function")
async def test_today_state_timestamps_are_utc_iso8601(client: AsyncClient, db_session):
    """generated_at is valid ISO 8601 with timezone info."""
    from datetime import datetime, timezone

    r = await client.get("/api/v1/today/state")
    assert r.status_code == 200
    data = r.json()

    # generated_at should parse as a UTC datetime
    generated = datetime.fromisoformat(data["generated_at"])
    # Should be within the last minute
    diff = (datetime.now(timezone.utc) - generated).total_seconds()
    assert 0 <= diff < 120, f"generated_at is {diff}s off from now"


# -- POST /today/mark-seen --


@pytest.mark.asyncio(loop_scope="function")
async def test_mark_seen_requires_auth(client: AsyncClient):
    """mark-seen must reject unauthenticated requests."""
    r = await client.post("/api/v1/today/mark-seen")
    assert r.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_mark_seen_first_time(client: AsyncClient, db_session):
    """First mark-seen: last_seen set to now, previous stays None."""
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.last_today_seen_at = None
    user.previous_today_seen_at = None
    await db_session.commit()

    before = datetime.now(timezone.utc)
    r = await client.post("/api/v1/today/mark-seen", cookies=_cookie("local-user"))
    assert r.status_code == 200

    # Reload user
    await db_session.refresh(user)
    assert user.last_today_seen_at is not None
    assert user.previous_today_seen_at is None
    # last_today_seen_at should be >= before
    assert user.last_today_seen_at >= before


@pytest.mark.asyncio(loop_scope="function")
async def test_mark_seen_shift(client: AsyncClient, db_session):
    """Subsequent mark-seen: last_seen shifts to previous, new last_seen set."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.core.ai_models import User

    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.last_today_seen_at = old_time
    user.previous_today_seen_at = None
    await db_session.commit()

    r = await client.post("/api/v1/today/mark-seen", cookies=_cookie("local-user"))
    assert r.status_code == 200

    await db_session.refresh(user)
    # previous should now hold the old last_seen
    assert user.previous_today_seen_at == old_time
    # last_seen should be newer
    assert user.last_today_seen_at > old_time


@pytest.mark.asyncio(loop_scope="function")
async def test_mark_seen_idempotent(client: AsyncClient, db_session):
    """Calling mark-seen twice in succession works correctly."""
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.last_today_seen_at = None
    user.previous_today_seen_at = None
    await db_session.commit()

    # First call
    r1 = await client.post("/api/v1/today/mark-seen", cookies=_cookie("local-user"))
    assert r1.status_code == 200

    await db_session.refresh(user)
    first_last = user.last_today_seen_at

    # Second call
    r2 = await client.post("/api/v1/today/mark-seen", cookies=_cookie("local-user"))
    assert r2.status_code == 200

    await db_session.refresh(user)
    # previous should now hold the first last_seen
    assert user.previous_today_seen_at == first_last
    # last_seen should be newer than first
    assert user.last_today_seen_at > first_last


@pytest.mark.asyncio(loop_scope="function")
async def test_mark_seen_utc_storage(client: AsyncClient, db_session):
    """mark-seen stores timestamps with UTC timezone."""
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    await db_session.commit()

    r = await client.post("/api/v1/today/mark-seen", cookies=_cookie("local-user"))
    assert r.status_code == 200

    await db_session.refresh(user)
    assert user.last_today_seen_at is not None
    # Should have UTC timezone
    assert user.last_today_seen_at.tzinfo is not None
    assert str(user.last_today_seen_at.tzinfo) == "UTC"


# -- Migration 0032 column defaults --


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_columns_default_null(client: AsyncClient, db_session):
    """New users start with both columns NULL (migration default)."""
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    # If migration hasn't been applied explicitly in test, columns may be None
    # (which is the correct default - nullable)
    # The model defines them as nullable=True, so they default to None
    assert getattr(user, "last_today_seen_at", None) is None or user.last_today_seen_at is None
    assert getattr(user, "previous_today_seen_at", None) is None or user.previous_today_seen_at is None


# -- Integration: state reflects mark-seen --


@pytest.mark.asyncio(loop_scope="function")
async def test_state_reflects_mark_seen(client: AsyncClient, db_session):
    """After mark-seen, state returns the updated last_seen_at."""
    from sqlalchemy import select

    from app.core.ai_models import User

    # Reset
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.last_today_seen_at = None
    user.previous_today_seen_at = None
    await db_session.commit()

    # State before: null
    r1 = await client.get("/api/v1/today/state", cookies=_cookie("local-user"))
    assert r1.json()["last_seen_at"] is None

    # Mark seen
    r2 = await client.post("/api/v1/today/mark-seen", cookies=_cookie("local-user"))
    assert r2.status_code == 200

    # State after: not null
    r3 = await client.get("/api/v1/today/state", cookies=_cookie("local-user"))
    assert r3.json()["last_seen_at"] is not None
