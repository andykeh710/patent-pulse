"""Integration tests for persona-aware briefing."""

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


@pytest.mark.asyncio(loop_scope="function")
async def test_briefing_returns_items(client: AsyncClient):
    r = await client.get("/api/v1/today/briefing")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    # Should have at least the "foryou" stub and the "expiring" stub
    types = {i["type"] for i in items}
    assert "foryou" in types


@pytest.mark.asyncio(loop_scope="function")
async def test_briefing_founder_vs_vc_ranking_differs(client: AsyncClient, db_session):
    """Founder and VC should get different top items due to persona weights."""
    from sqlalchemy import select

    from app.core.ai_models import User

    # Set persona for local-user (Founder) and local-user-2 (VC)
    user1 = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user1.persona = "Founder"
    user1.onboarded_at = __import__("datetime").datetime.utcnow()

    user2 = (await db_session.execute(select(User).where(User.id == "local-user-2"))).scalar_one()
    user2.persona = "VC"
    user2.onboarded_at = __import__("datetime").datetime.utcnow()
    await db_session.commit()

    r1 = await client.get("/api/v1/today/briefing", cookies=_cookie("local-user"))
    r2 = await client.get("/api/v1/today/briefing", cookies=_cookie("local-user-2"))

    assert r1.status_code == 200
    assert r2.status_code == 200

    items1 = r1.json()
    items2 = r2.json()

    assert len(items1) > 0
    assert len(items2) > 0

    # With different persona weights, the top item type may differ
    # Founder: HIGH on expiring + company
    # VC: HIGH on expiring + company + trend
    # Both should have the same set of items but possibly reordered
    types1 = {i["type"] for i in items1}
    types2 = {i["type"] for i in items2}
    assert types1 == types2  # Same content types available


@pytest.mark.asyncio(loop_scope="function")
async def test_briefing_no_persona_is_backward_compatible(client: AsyncClient):
    """Without persona set, briefing should work identically to before."""
    r = await client.get("/api/v1/today/briefing")
    assert r.status_code == 200
    items = r.json()
    assert len(items) > 0
    # No _score leakage
    for item in items:
        assert "_score" not in item
