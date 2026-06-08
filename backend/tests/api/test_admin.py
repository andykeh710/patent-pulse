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


# ── Phase 1: Embedding admin tests ───────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_embedding_stats_requires_admin(client, db_session):
    r = await client.get("/api/v1/admin/embedding-stats")
    assert r.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_embedding_stats_returns_coverage(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User
    from app.core.models import PatentPublication

    user = (await db_session.execute(
        select(User).where(User.id == "local-user")
    )).scalar_one()
    user.is_admin = True
    await db_session.commit()

    # Seed a few patents, some with embeddings
    db_session.add(PatentPublication(
        doc_id="USPTO:EMBSTAT1",
        publication_number="EMBSTAT1",
        office="USPTO",
        title="Patent with embedding",
        abstract="Has vector",
        embedding=[1.0] * 1536,
    ))
    db_session.add(PatentPublication(
        doc_id="USPTO:EMBSTAT2",
        publication_number="EMBSTAT2",
        office="USPTO",
        title="Patent without embedding",
        abstract="No vector",
        embedding=None,
    ))
    await db_session.commit()

    r = await client.get("/api/v1/admin/embedding-stats", cookies=_cookie())
    assert r.status_code == 200
    data = r.json()
    assert data["total_patents"] >= 2
    assert data["embedded"] >= 1
    assert data["missing"] >= 1
    assert 0 < data["coverage_pct"] < 100


@pytest.mark.asyncio(loop_scope="function")
async def test_re_embed_patent_not_found(client, db_session):
    from sqlalchemy import select

    from app.core.ai_models import User

    user = (await db_session.execute(
        select(User).where(User.id == "local-user")
    )).scalar_one()
    user.is_admin = True
    await db_session.commit()

    r = await client.post(
        "/api/v1/admin/embed/00000000-0000-0000-0000-000000000000",
        cookies=_cookie(),
    )
    assert r.status_code == 404


@pytest.mark.asyncio(loop_scope="function")
async def test_re_embed_patent_success(client, db_session):
    import uuid
    from unittest.mock import patch

    from sqlalchemy import select

    from app.ai.embedder import PatentEmbedder
    from app.core.ai_models import User
    from app.core.models import PatentPublication

    user = (await db_session.execute(
        select(User).where(User.id == "local-user")
    )).scalar_one()
    user.is_admin = True
    await db_session.commit()

    patent_id = uuid.uuid4()
    db_session.add(PatentPublication(
        id=patent_id,
        doc_id="USPTO:REEMB1",
        publication_number="REEMB1",
        office="USPTO",
        title="Patent for re-embed test",
        abstract="This patent needs an embedding",
        embedding=None,
    ))
    await db_session.commit()

    fake_emb = [0.5] * 1536
    with patch.object(PatentEmbedder, "generate_patent_embedding", return_value=fake_emb):
        r = await client.post(
            f"/api/v1/admin/embed/{patent_id}",
            cookies=_cookie(),
        )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "re-embedded"
    assert data["dimensions"] == 1536
