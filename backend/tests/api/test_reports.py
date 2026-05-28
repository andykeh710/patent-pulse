"""Tests for PDF report endpoint (Sprint 7)."""
import uuid
from unittest.mock import patch

import pytest


def _make_cookie(user_id="local-user"):
    from datetime import datetime, timedelta, timezone

    import jwt

    from app.config import settings
    return jwt.encode(
        {"sub": user_id, "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(days=30)},
        settings.auth_secret_key, algorithm="HS256",
    )


def _auth(client):
    client.cookies.set("auth_session", _make_cookie())


@pytest.mark.asyncio(loop_scope="function")
async def test_free_user_gets_402(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "free"
    await db_session.commit()

    _auth(client)
    r = await client.post(f"/api/v1/patents/{uuid.uuid4()}/report")
    assert r.status_code == 402


@pytest.mark.asyncio(loop_scope="function")
async def test_basic_user_gets_402(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "basic"
    await db_session.commit()

    _auth(client)
    r = await client.post(f"/api/v1/patents/{uuid.uuid4()}/report")
    assert r.status_code == 402


@pytest.mark.asyncio(loop_scope="function")
async def test_lifetime_user_gets_pdf(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User
    from app.core.models import PatentPublication
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "lifetime"
    await db_session.commit()

    patent = PatentPublication(
        doc_id="USPTO:pdf-test", publication_number="PDF001", office="USPTO",
        title="PDF Test Patent", assignees=["TestCo"], cpc=["G06F"],
    )
    db_session.add(patent)
    await db_session.commit()

    with patch("app.reports.pdf_generator._render_pdf") as mock_pdf:
        mock_pdf.return_value = b"%PDF-1.4 fake pdf"
        _auth(client)
        r = await client.post(f"/api/v1/patents/{patent.id}/report")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF-")


@pytest.mark.asyncio(loop_scope="function")
async def test_patent_not_found_returns_404(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "lifetime"
    await db_session.commit()

    _auth(client)
    r = await client.post(f"/api/v1/patents/{uuid.uuid4()}/report")
    assert r.status_code == 404


@pytest.mark.asyncio(loop_scope="function")
async def test_export_row_written(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User
    from app.core.billing_models import Export
    from app.core.models import PatentPublication
    user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
    user.tier = "lifetime"
    await db_session.commit()

    patent = PatentPublication(
        doc_id="USPTO:pdf-export", publication_number="PDFEXP", office="USPTO",
        title="PDF Export", assignees=["E"], cpc=["G06F"],
    )
    db_session.add(patent)
    await db_session.commit()

    with patch("app.reports.pdf_generator._render_pdf") as mock_pdf:
        mock_pdf.return_value = b"%PDF-1.4 x"
        _auth(client)
        r = await client.post(f"/api/v1/patents/{patent.id}/report")
        assert r.status_code == 200

    export = (await db_session.execute(
        select(Export).where(Export.user_id == "local-user")
    )).scalars().first()
    assert export is not None
    assert export.export_type == "pdf"


def test_forbidden_phrase_filtered():
    from app.reports.pdf_generator import _filter_forbidden
    assert _filter_forbidden("is used by Acme Corp") == "[filtered] Acme Corp"
    assert _filter_forbidden("definitely used in production") == "[filtered] in production"


@pytest.mark.asyncio(loop_scope="function")
async def test_no_auth_returns_401(client):
    r = await client.post(f"/api/v1/patents/{uuid.uuid4()}/report")
    assert r.status_code == 401
