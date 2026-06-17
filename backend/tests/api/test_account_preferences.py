from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.config import settings
from app.core.ai_models import User, UserCompanyFollow


def _cookie(user_id: str = "local-user") -> dict[str, str]:
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
async def test_set_persona_updates_authenticated_user(
    client: AsyncClient,
    db_session,
) -> None:
    response = await client.put(
        "/api/v1/account/persona",
        json={"persona": "operator"},
        cookies=_cookie(),
    )

    assert response.status_code == 200
    assert response.json() == {"persona": "operator"}

    user = (
        await db_session.execute(select(User).where(User.id == "local-user"))
    ).scalar_one()
    assert user.persona == "operator"


@pytest.mark.asyncio(loop_scope="function")
async def test_update_email_preferences_updates_authenticated_user(
    client: AsyncClient,
    db_session,
) -> None:
    response = await client.put(
        "/api/v1/account/email-preferences",
        json={"weekly_briefing_enabled": False, "instant_alerts_enabled": True},
        cookies=_cookie(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "weekly_briefing_enabled": False,
        "instant_alerts_enabled": True,
    }

    user = (
        await db_session.execute(select(User).where(User.id == "local-user"))
    ).scalar_one()
    assert user.preferences == {
        "weekly_briefing_enabled": False,
        "instant_alerts_enabled": True,
    }


@pytest.mark.asyncio(loop_scope="function")
async def test_company_follow_routes_use_authenticated_user(
    client: AsyncClient,
    db_session,
) -> None:
    create_response = await client.post(
        "/api/v1/account/companies",
        json={"company_name": "Acme Corp"},
        cookies=_cookie(),
    )

    assert create_response.status_code == 201
    assert create_response.json() == {
        "company_normalized_name": "acme",
        "display_name": "Acme Corp",
    }

    list_response = await client.get("/api/v1/account/companies", cookies=_cookie())
    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "company_normalized_name": "acme",
            "display_name": "Acme Corp",
        }
    ]

    delete_response = await client.delete(
        "/api/v1/account/companies/acme",
        cookies=_cookie(),
    )
    assert delete_response.status_code == 204

    follow = (
        await db_session.execute(
            select(UserCompanyFollow).where(
                UserCompanyFollow.user_id == "local-user",
                UserCompanyFollow.company_normalized_name == "acme",
            )
        )
    ).scalar_one_or_none()
    assert follow is None
