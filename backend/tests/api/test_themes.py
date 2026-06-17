"""
Tests for the themes/topics API and matching logic.

Covers Phase 3 extensions: keywords, opportunity_tags, min_opportunity_score,
user_id fields, and keyword-based matching.
"""

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.models import PatentPublication
from app.core.theme_models import Theme, ThemeMatch
from app.tasks.theme_matcher import _calculate_match_score, _match_single_theme


def _cookie(user_id: str = "local-user") -> dict:
    """Auth cookie for an existing seeded test user. Topic create/delete are
    user-scoped (commit cff99ca), so these calls must be authenticated."""
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
    fields and scopes the topic to the authenticated user."""
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
    # Topic is owned by the authenticated user (body user_id is ignored).
    assert body["user_id"] == "local-user"


@pytest.mark.asyncio
async def test_create_topic_requires_auth(client, db_session):
    """Creating a topic without a session cookie returns 401, not 500."""
    response = await client.post("/api/v1/themes", json={"name": "No Auth Topic"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_topic_ignores_body_user_id(client, db_session):
    """A body user_id cannot reassign ownership — the session user wins."""
    response = await client.post("/api/v1/themes", json={
        "name": "Alice's Topic",
        "user_id": "alice",
    }, cookies=_cookie("local-user"))
    assert response.status_code == 200
    assert response.json()["user_id"] == "local-user"


@pytest.mark.asyncio
async def test_create_topic_duplicate_name_fails(client, db_session):
    """Second create with same name returns 400."""
    await client.post("/api/v1/themes", json={"name": "Duplicate"}, cookies=_cookie())
    response = await client.post("/api/v1/themes", json={"name": "Duplicate"}, cookies=_cookie())
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


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
async def test_update_topic_requires_auth(client, db_session):
    """PATCH without a session cookie returns 401, not 500/200."""
    response = await client.post(
        "/api/v1/themes", json={"name": "Auth Patch Topic"}, cookies=_cookie()
    )
    topic_id = response.json()["id"]

    response = await client.patch(
        f"/api/v1/themes/{topic_id}", json={"description": "no auth"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_other_users_topic_forbidden(client, db_session):
    """A user cannot edit a topic owned by someone else."""
    response = await client.post(
        "/api/v1/themes", json={"name": "Owned By One"}, cookies=_cookie("local-user")
    )
    topic_id = response.json()["id"]

    response = await client.patch(
        f"/api/v1/themes/{topic_id}",
        json={"description": "hijack"},
        cookies=_cookie("local-user-2"),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_system_theme_forbidden_for_normal_user(client, db_session):
    """System themes (user_id IS NULL) cannot be edited by a normal user."""
    sys_theme = Theme(name="System Editable Test", cpc_prefixes=["G06F"], user_id=None)
    db_session.add(sys_theme)
    await db_session.commit()

    response = await client.patch(
        f"/api/v1/themes/{sys_theme.id}",
        json={"description": "tamper"},
        cookies=_cookie("local-user"),  # seeded user is non-admin by default
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_system_theme_allowed_for_admin(client, db_session):
    """An admin may edit system themes (admin edit path)."""
    from app.core.ai_models import User

    admin = (
        await db_session.execute(select(User).where(User.id == "local-user"))
    ).scalar_one()
    admin.is_admin = True
    sys_theme = Theme(name="System Admin Editable", cpc_prefixes=["G06F"], user_id=None)
    db_session.add(sys_theme)
    await db_session.commit()

    response = await client.patch(
        f"/api/v1/themes/{sys_theme.id}",
        json={"description": "official update"},
        cookies=_cookie("local-user"),
    )
    assert response.status_code == 200
    assert response.json()["description"] == "official update"


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
    """DELETE unknown UUID returns 404 (authenticated)."""
    fake_id = str(uuid4())
    response = await client.delete(f"/api/v1/themes/{fake_id}", cookies=_cookie())
    assert response.status_code == 404


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


# ---------------------------------------------------------------------------
# Theme matcher — false-positive prevention (whole-word matching)
# ---------------------------------------------------------------------------

def _patent(**kw) -> PatentPublication:
    base = dict(
        doc_id="USPTO:FP001", office="USPTO", publication_number="FP001",
        assignees=[], cpc=[], title="", abstract="", legal_status="GRANTED",
    )
    base.update(kw)
    return PatentPublication(**base)


def test_short_keyword_does_not_substring_match_assignee():
    """'AI' must NOT match the substring inside 'HYUNDAI' (the original bug)."""
    patent = _patent(
        assignees=["HYUNDAI MOTOR CO"],
        title="Automotive hot gas heat pump system",
        cpc=["F25B30/00"],
    )
    theme = Theme(name="AI", assignee_keywords=["AI"], title_keywords=[],
                  keywords=[], cpc_prefixes=[])
    score, reasons = _calculate_match_score(patent, theme)
    assert score == 0.0, f"AI should not match Hyundai; got {reasons}"


def test_short_keyword_does_not_substring_match_title():
    """A 'die' keyword must not match 'studied' / 'diesel' in a title."""
    patent = _patent(title="A diesel engine studied under load", cpc=[])
    theme = Theme(name="Chip", keywords=["die"], cpc_prefixes=[],
                  assignee_keywords=[], title_keywords=[])
    score, _ = _calculate_match_score(patent, theme)
    assert score == 0.0


def test_whole_word_keyword_still_matches():
    """Whole-word keywords still match legitimately."""
    patent = _patent(
        assignees=["AI Research Labs"],
        title="Neural network training for deep learning",
        cpc=["G06N3/08"],
    )
    theme = Theme(
        name="AI / Machine Learning", cpc_prefixes=["G06N"],
        assignee_keywords=["AI"], title_keywords=["neural network"],
        keywords=["deep learning"],
    )
    score, reasons = _calculate_match_score(patent, theme)
    assert score > 0
    assert any("CPC" in r for r in reasons)
    assert any("neural network" in r.lower() for r in reasons)
    assert any("AI" in r for r in reasons)
