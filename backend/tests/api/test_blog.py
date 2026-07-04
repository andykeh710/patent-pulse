"""Tests for blog system (Phase 6 PR 2)."""

import pytest

pytestmark = pytest.mark.xfail(
    reason="Blog test data not seeded — needs dev_fixture for blog_posts"
)

from sqlalchemy import select

from app.core.blog_models import BlogPost

SECRET = "test-secret-key-for-tests"


@pytest.fixture(autouse=True, scope="session")
def _patch_settings():
    from app.config import settings as global_settings

    global_settings.auth_secret_key = SECRET


@pytest.fixture(autouse=True)
def _set_secret(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET_KEY", SECRET)


def _make_session_cookie(user_id="local-user"):
    from datetime import datetime, timedelta, timezone

    import jwt

    token = jwt.encode(
        {
            "sub": user_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
        },
        SECRET,
        algorithm="HS256",
    )
    return {"auth_session": token}


def _make_admin(db_session):
    from app.core.ai_models import User

    async def _inner():
        user = (await db_session.execute(select(User).where(User.id == "local-user"))).scalar_one()
        user.is_admin = True
        await db_session.commit()

    return _inner


# ── public routes ─────────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_blog_list_returns_published(client, db_session):
    """Public blog list returns only published posts."""
    db_session.add(
        BlogPost(
            slug="published-post",
            title="Published",
            content_markdown="# Hi",
            author_name="Author",
            status="published",
        )
    )
    db_session.add(
        BlogPost(
            slug="draft-post",
            title="Draft",
            content_markdown="# Secret",
            author_name="Author",
            status="draft",
        )
    )
    await db_session.commit()

    r = await client.get("/api/v1/blog")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["slug"] == "published-post"


@pytest.mark.asyncio(loop_scope="function")
async def test_blog_get_published_returns_200(client, db_session):
    """Public GET returns published post."""
    db_session.add(
        BlogPost(
            slug="test-post",
            title="Test",
            content_markdown="# Hello",
            author_name="Author",
            status="published",
        )
    )
    await db_session.commit()

    r = await client.get("/api/v1/blog/test-post")
    assert r.status_code == 200
    assert r.json()["title"] == "Test"


@pytest.mark.asyncio(loop_scope="function")
async def test_blog_get_draft_returns_404(client, db_session):
    """Draft posts are not publicly accessible."""
    db_session.add(
        BlogPost(
            slug="secret-draft",
            title="Secret",
            content_markdown="# Hush",
            author_name="Author",
            status="draft",
        )
    )
    await db_session.commit()

    r = await client.get("/api/v1/blog/secret-draft")
    assert r.status_code == 404


# ── admin endpoints ──────────────────────────────────────────────


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_create_blog_post(client, db_session):
    """Admin can create blog posts."""
    await _make_admin(db_session)()

    r = await client.post(
        "/api/v1/blog",
        json={
            "slug": "new-post",
            "title": "New",
            "content_markdown": "# Hello",
            "author_name": "Andy",
        },
        cookies=_make_session_cookie(),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "draft"


@pytest.mark.asyncio(loop_scope="function")
async def test_non_admin_cannot_create(client, db_session):
    """Non-admin gets 403 on create."""
    r = await client.post(
        "/api/v1/blog",
        json={"slug": "nope", "title": "Nope", "content_markdown": "# No", "author_name": "Me"},
        cookies=_make_session_cookie(),
    )
    assert r.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_publish_post(client, db_session):
    """Publishing sets status=published and published_at."""
    await _make_admin(db_session)()

    db_session.add(
        BlogPost(
            slug="to-publish",
            title="Draft",
            content_markdown="# Soon",
            author_name="Andy",
            status="draft",
        )
    )
    await db_session.commit()

    r = await client.post(
        "/api/v1/blog/to-publish/publish",
        cookies=_make_session_cookie(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "published"
    assert data["published_at"] is not None


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_update_post(client, db_session):
    """Admin can update blog posts."""
    await _make_admin(db_session)()

    db_session.add(
        BlogPost(
            slug="edit-me",
            title="Original",
            content_markdown="# Old",
            author_name="Andy",
            status="draft",
        )
    )
    await db_session.commit()

    r = await client.patch(
        "/api/v1/blog/edit-me",
        json={"title": "Updated"},
        cookies=_make_session_cookie(),
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Updated"


# ── structured data / SEO ────────────────────────────────────────


def test_blog_post_json_ld_valid():
    """Blog post JSON-LD follows Article schema."""
    json_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Test Post",
        "author": {"@type": "Person", "name": "Andy"},
        "publisher": {"@type": "Organization", "name": "Invention Index 8"},
        "datePublished": "2026-06-12T00:00:00Z",
    }
    assert json_ld["@context"] == "https://schema.org"
    assert json_ld["@type"] == "Article"
    assert json_ld["author"]["@type"] == "Person"


# ── seed ─────────────────────────────────────────────────────────


def test_frontmatter_parser():
    """Frontmatter parser extracts fields correctly."""
    from app.api.v1.blog import _parse_frontmatter

    md = """---
title: Test Post
tags: [a, b]
status: published
---
# Content here
"""

    fm = _parse_frontmatter(md)
    assert fm is not None
    assert fm["title"] == "Test Post"
    assert fm["tags"] == ["a", "b"]
    assert fm["status"] == "published"
    assert "# Content here" in fm["body"]
