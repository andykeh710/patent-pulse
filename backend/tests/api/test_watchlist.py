from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.config import settings
from app.core.models import PatentPublication
from app.core.theme_models import WatchlistItem


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


async def _seed_patent(db_session, publication_number: str = "WATCH001"):
    patent = PatentPublication(
        doc_id=f"USPTO:{publication_number}",
        office="USPTO",
        publication_number=publication_number,
        title="Watchlist isolation test patent",
        legal_status="GRANTED",
    )
    db_session.add(patent)
    await db_session.commit()
    await db_session.refresh(patent)
    return patent


@pytest.mark.asyncio(loop_scope="function")
async def test_watchlist_add_requires_auth(client: AsyncClient, db_session):
    patent = await _seed_patent(db_session)

    response = await client.post(
        "/api/v1/watchlist",
        json={"patent_id": str(patent.id)},
    )

    assert response.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_watchlist_items_are_scoped_to_authenticated_user(
    client: AsyncClient,
    db_session,
):
    patent = await _seed_patent(db_session, "WATCH002")

    first = await client.post(
        "/api/v1/watchlist",
        json={"patent_id": str(patent.id), "note": "first user"},
        cookies=_cookie("local-user"),
    )
    second = await client.post(
        "/api/v1/watchlist",
        json={"patent_id": str(patent.id), "note": "second user"},
        cookies=_cookie("local-user-2"),
    )

    assert first.status_code == 200
    assert second.status_code == 200

    first_list = await client.get("/api/v1/watchlist", cookies=_cookie("local-user"))
    second_list = await client.get("/api/v1/watchlist", cookies=_cookie("local-user-2"))

    assert [item["note"] for item in first_list.json()] == ["first user"]
    assert [item["note"] for item in second_list.json()] == ["second user"]

    rows = (await db_session.execute(select(WatchlistItem))).scalars().all()
    assert sorted(row.user_id for row in rows) == ["local-user", "local-user-2"]
