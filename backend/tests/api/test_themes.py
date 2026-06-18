"""
Tests for the themes/topics API and matching logic.

Covers Phase 3 extensions: keywords, opportunity_tags, min_opportunity_score,
user_id fields, and keyword-based matching.
"""

from uuid import uuid4

import jwt
import pytest
from sqlalchemy import select

from app.config import settings
from app.core.models import PatentPublication
from app.core.theme_models import Theme, ThemeMatch
from app.tasks.theme_matcher import _match_single_theme


def _cookie(user_id: str = "local-user") -> dict[str, str]:
    from datetime import datetime, timedelta, timezone

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

# ---------------------------------------------------------------------------
# List / get
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_list_themes_includes_system_and_user(client, db_session):
    """List endpoint returns both system themes (user_id=None) and user topics."""
    db_session.add_all([
        Theme(name="System Theme", cpc_prefixes=["G06F"], user_id=None),
        Theme(name="User Topic", cpc_prefixes=["H04L"], user_id="anonymous"),
    ])
    await db_session.commit()

    response = await client.get("/api/v1/themes")
    assert response.status_code == 200

    body = response.json()
    assert len(body) == 5  # 2 test-added + 3 conftest-seeded

    # At least one system theme (user_id=None) and one user topic present
    user_ids = [t["user_id"] for t in body]
    assert None in user_ids, "Should have at least one system theme (user_id=None)"
    assert "anonymous" in user_ids, "Should have at least one user topic (user_id='anonymous')"


@pytest.mark.asyncio
async def test_get_topic_by_id(client, db_session):
    """Round-trip: create via POST, GET by id matches."""
    response = await client.post("/api/v1/themes", json={
        "name": "Roundtrip Topic",
        "cpc_prefixes": ["G06N"],
        "keywords": ["neural", "transformer"],
    }, cookies=_cookie())
    assert response.status_code == 200
    created = response.json()

    response = await client.get(f"/api/v1/themes/{created['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Roundtrip Topic"
    assert body["cpc_prefixes"] == ["G06N"]
    assert body["keywords"] == ["neural", "transformer"]


@pytest.mark.asyncio
async def test_get_topic_404(client, db_session):
    """Unknown UUID returns 404."""
    fake_id = str(uuid4())
    response = await client.get(f"/api/v1/themes/{fake_id}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_topic_with_keywords(client, db_session):
    """POST with keywords, opportunity_tags, min_opportunity_score echoes all
    fields and defaults user_id to 'anonymous'."""
    response = await client.post("/api/v1/themes", json={
        "name": "AI Safety",
        "description": "Alignment and safety research",
        "cpc_prefixes": ["G06N", "G06F"],
        "keywords": ["alignment", "safety", "RLHF"],
        "opportunity_tags": ["startup", "enterprise"],
        "min_opportunity_score": 35,
    }, cookies=_cookie())
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "AI Safety"
    assert body["description"] == "Alignment and safety research"
    assert body["cpc_prefixes"] == ["G06N", "G06F"]
    assert body["keywords"] == ["alignment", "safety", "RLHF"]
    assert body["opportunity_tags"] == ["startup", "enterprise"]
    assert body["min_opportunity_score"] == 35
    assert body["user_id"] == "local-user"


@pytest.mark.asyncio
async def test_create_topic_ignores_spoofed_user_id(client, db_session):
    """The authenticated user owns created topics, regardless of request body."""
    response = await client.post("/api/v1/themes", json={
        "name": "Alice's Topic",
        "user_id": "alice",
    }, cookies=_cookie())
    assert response.status_code == 200
    assert response.json()["user_id"] == "local-user"


@pytest.mark.asyncio
async def test_create_topic_duplicate_name_fails(client, db_session):
    """Second create with same name returns 400."""
    await client.post("/api/v1/themes", json={"name": "Duplicate"}, cookies=_cookie())
    response = await client.post("/api/v1/themes", json={"name": "Duplicate"}, cookies=_cookie())
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_topic_requires_auth(client, db_session):
    """Anonymous clients cannot create shared topics."""
    response = await client.post("/api/v1/themes", json={"name": "Anonymous Topic"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_topic_partial(client, db_session):
    """PATCH a single field, others remain unchanged."""
    # Create
    response = await client.post("/api/v1/themes", json={
        "name": "Orig Name",
        "description": "Orig desc",
        "cpc_prefixes": ["A61K"],
        "keywords": ["crispr"],
    }, cookies=_cookie())
    topic_id = response.json()["id"]

    # Patch description only
    response = await client.patch(f"/api/v1/themes/{topic_id}", json={
        "description": "Updated desc",
    }, cookies=_cookie())
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Orig Name"
    assert body["description"] == "Updated desc"
    assert body["cpc_prefixes"] == ["A61K"]
    assert body["keywords"] == ["crispr"]


@pytest.mark.asyncio
async def test_update_topic_keywords_replaces_list(client, db_session):
    """PATCH keywords fully replaces the prior list (not append)."""
    response = await client.post("/api/v1/themes", json={
        "name": "Keyword Topic",
        "keywords": ["a", "b", "c"],
    }, cookies=_cookie())
    topic_id = response.json()["id"]

    response = await client.patch(f"/api/v1/themes/{topic_id}", json={
        "keywords": ["x", "y"],
    }, cookies=_cookie())
    assert response.status_code == 200
    assert response.json()["keywords"] == ["x", "y"]


@pytest.mark.asyncio
async def test_update_topic_requires_owner(client, db_session):
    """Users cannot update system themes or topics owned by another user."""
    theme = Theme(name="Protected System Topic", user_id=None, cpc_prefixes=["G06F"])
    db_session.add(theme)
    await db_session.commit()
    await db_session.refresh(theme)

    response = await client.patch(
        f"/api/v1/themes/{theme.id}",
        json={"name": "Compromised"},
        cookies=_cookie(),
    )

    assert response.status_code == 404

    refreshed = (
        await db_session.execute(select(Theme).where(Theme.id == theme.id))
    ).scalar_one()
    assert refreshed.name == "Protected System Topic"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_topic(client, db_session):
    """DELETE returns success; GET afterward returns 404."""
    response = await client.post("/api/v1/themes", json={"name": "ToDelete"}, cookies=_cookie())
    topic_id = response.json()["id"]

    response = await client.delete(f"/api/v1/themes/{topic_id}", cookies=_cookie())
    assert response.status_code == 200
    assert response.json()["deleted"] is True

    response = await client.get(f"/api/v1/themes/{topic_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_topic_404(client, db_session):
    """DELETE unknown UUID returns 404."""
    fake_id = str(uuid4())
    response = await client.delete(f"/api/v1/themes/{fake_id}", cookies=_cookie())
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_topic_requires_auth(client, db_session):
    """Anonymous clients cannot delete topics."""
    theme = Theme(name="Anonymous Delete Target", user_id="local-user", cpc_prefixes=["G06F"])
    db_session.add(theme)
    await db_session.commit()
    await db_session.refresh(theme)

    response = await client.delete(f"/api/v1/themes/{theme.id}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_topic_requires_owner(client, db_session):
    """Users cannot delete system themes or another user's topics."""
    theme = Theme(name="Protected Delete Target", user_id=None, cpc_prefixes=["G06F"])
    db_session.add(theme)
    await db_session.commit()
    await db_session.refresh(theme)

    response = await client.delete(f"/api/v1/themes/{theme.id}", cookies=_cookie())

    assert response.status_code == 404
    assert (
        await db_session.execute(select(Theme).where(Theme.id == theme.id))
    ).scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Theme matcher — keyword matching
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_theme_matcher_uses_keywords(client, db_session):
    """Create a topic with keywords=['quantum'], seed a patent with 'quantum'
    in the title, run the matcher directly, assert a ThemeMatch row is produced
    with reasons mentioning the keyword."""
    # Seed patent
    patent = PatentPublication(
        doc_id="USPTO:QUANTUM001",
        office="USPTO",
        publication_number="QUANTUM001",
        assignees=["Quantum Labs"],
        cpc=["G06N"],
        title="Quantum error correction for superconducting qubits",
        abstract="A method for reducing decoherence in quantum processors.",
        legal_status="GRANTED",
    )
    db_session.add(patent)
    await db_session.flush()

    # Create topic with keyword matching
    topic = Theme(
        name="Quantum Computing Test",
        cpc_prefixes=[],
        keywords=["quantum"],
        user_id="anonymous",
    )
    db_session.add(topic)
    await db_session.commit()

    # Run matcher directly (bypass Celery — use the test session)
    stats = await _match_single_theme(db_session, topic, limit=100)
    assert stats["matched"] >= 1

    # Verify ThemeMatch row
    result = await db_session.execute(
        select(ThemeMatch).where(
            ThemeMatch.theme_id == topic.id,
            ThemeMatch.patent_id == patent.id,
        )
    )
    match = result.scalar_one_or_none()
    assert match is not None
    assert match.match_score > 0
    assert any("quantum" in reason.lower() for reason in match.match_reasons), \
        f"Expected keyword reason in {match.match_reasons}"
