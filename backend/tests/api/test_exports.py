"""Tests for CSV export endpoint (Sprint 7)."""
import io
import csv

import pytest


def _make_cookie(user_id="local-user"):
    import jwt
    from datetime import datetime, timedelta, timezone
    from app.config import settings
    return jwt.encode(
        {"sub": user_id, "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(days=30)},
        settings.auth_secret_key, algorithm="HS256",
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_free_user_gets_402(client, db_session):
    from app.core.ai_models import User
    from sqlalchemy import select
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "free"
    await db_session.commit()

    r = await client.get("/api/v1/exports/expiry.csv", cookies={"auth_session": _make_cookie()})
    assert r.status_code == 402


@pytest.mark.asyncio(loop_scope="function")
async def test_basic_user_gets_csv(client, db_session):
    from app.core.ai_models import User
    from sqlalchemy import select
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "basic"
    await db_session.commit()

    r = await client.get("/api/v1/exports/expiry.csv", cookies={"auth_session": _make_cookie()})
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "expiry-" in r.headers.get("content-disposition", "")

    reader = csv.reader(io.StringIO(r.text))
    header = next(reader)
    assert "doc_id" in header
    assert len(header) == 17


@pytest.mark.asyncio(loop_scope="function")
async def test_export_row_written(client, db_session):
    from app.core.ai_models import User
    from sqlalchemy import select
    from app.core.billing_models import Export

    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "basic"
    await db_session.commit()

    r = await client.get("/api/v1/exports/expiry.csv", cookies={"auth_session": _make_cookie()})
    assert r.status_code == 200

    export = (await db_session.execute(
        select(Export).where(Export.user_id == "local-user")
    )).scalars().first()
    assert export is not None
    assert export.export_type == "csv"
    assert export.scope == "expiry_list"


@pytest.mark.asyncio(loop_scope="function")
async def test_empty_result_returns_header_only(client, db_session):
    from app.core.ai_models import User
    from sqlalchemy import select
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "basic"
    await db_session.commit()

    r = await client.get("/api/v1/exports/expiry.csv?expiry_status=nonexistent", cookies={"auth_session": _make_cookie()})
    assert r.status_code == 200
    lines = r.text.strip().split("\n")
    assert len(lines) == 1


@pytest.mark.asyncio(loop_scope="function")
async def test_no_auth_returns_401(client):
    r = await client.get("/api/v1/exports/expiry.csv")
    assert r.status_code == 401
