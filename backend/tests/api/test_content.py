"""Tests for content generation API endpoints."""
from uuid import uuid4, UUID

import pytest
from sqlalchemy import select

from app.core.ai_models import AIArtifact, ContentDraft
from app.core.models import PatentPublication


async def _make_artifact(db_session) -> UUID:
    """Create a minimal AIArtifact row so the content_draft FK resolves."""
    artifact = AIArtifact(
        artifact_type="linkedin_post",
        artifact_version=1,
        model="claude-haiku",
        prompt_name="linkedin_post",
        prompt_version=1,
        prompt_hash="test_hash",
        input_hash="test_input_hash",
        status="complete",
        content_json={"test": True},
    )
    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)
    return artifact.id


@pytest.mark.asyncio
async def test_generate_linkedin_post_success(client, db_session):
    """POST generate-linkedin returns 200 with full response shape."""
    patent = PatentPublication(
        doc_id="USPTO:LP001",
        office="USPTO",
        publication_number="LP001",
        assignees=["TestCorp"],
        cpc=["G06F"],
        title="A system for testing content generation",
        abstract="This is a test patent abstract with enough text.",
        legal_status="GRANTED",
    )
    db_session.add(patent)
    await db_session.commit()

    artifact_id = await _make_artifact(db_session)

    fake_data = {
        "post_markdown": "**Test Post**\n\nThis is a generated LinkedIn post about testing.",
        "hook": "Testing hooks for content generation",
        "tone": "analytical",
        "caveats": ["Test caveat 1", "Test caveat 2"],
    }

    from unittest.mock import AsyncMock, patch
    with patch("app.api.v1.content.generate_linkedin_post", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = (fake_data, artifact_id)
        response = await client.post("/api/v1/content/generate-linkedin", json={
            "patent_id": str(patent.id),
            "tone": "analytical",
        })

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "Test Post" in body["post_markdown"]
    assert body["hook"] == "Testing hooks for content generation"
    assert body["tone"] == "analytical"
    assert len(body["caveats"]) == 2
    assert body["artifact_id"] is not None
    assert body["draft_id"] is not None
    assert "LP001" in body["source_citation"]


@pytest.mark.asyncio
async def test_generate_linkedin_post_patent_not_found(client, db_session):
    """POST with unknown patent_id returns 404."""
    fake_id = str(uuid4())
    response = await client.post("/api/v1/content/generate-linkedin", json={
        "patent_id": fake_id,
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_linkedin_post_no_title_or_abstract(client, db_session):
    """POST with patent lacking title AND abstract returns 400."""
    patent = PatentPublication(
        doc_id="USPTO:LP002",
        office="USPTO",
        publication_number="LP002",
        assignees=["EmptyCorp"],
        cpc=["A61B"],
        title=None,
        abstract=None,
        legal_status="PUBLISHED",
    )
    db_session.add(patent)
    await db_session.commit()

    response = await client.post("/api/v1/content/generate-linkedin", json={
        "patent_id": str(patent.id),
    })
    assert response.status_code == 400
    assert "title or abstract" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_linkedin_post_creates_draft_row(client, db_session):
    """After success, a ContentDraft row exists with correct fields."""
    patent = PatentPublication(
        doc_id="USPTO:LP003",
        office="USPTO",
        publication_number="LP003",
        assignees=["DraftCorp"],
        cpc=["H04L"],
        title="Draft creation test patent",
        abstract="Testing that draft rows are persisted correctly.",
        legal_status="GRANTED",
    )
    db_session.add(patent)
    await db_session.commit()

    artifact_id = await _make_artifact(db_session)

    fake_data = {
        "post_markdown": "Draft row test content.",
        "hook": "Draft hook",
        "tone": "news",
        "caveats": [],
    }

    from unittest.mock import AsyncMock, patch
    with patch("app.api.v1.content.generate_linkedin_post", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = (fake_data, artifact_id)
        await client.post("/api/v1/content/generate-linkedin", json={
            "patent_id": str(patent.id),
        })

    result = await db_session.execute(
        select(ContentDraft).where(ContentDraft.source_id == patent.id)
    )
    draft = result.scalar_one_or_none()
    assert draft is not None
    assert draft.content_type == "linkedin_post"
    assert draft.source_type == "patent"
    assert draft.user_id == "anonymous"
    assert draft.content_text == "Draft row test content."


@pytest.mark.asyncio
async def test_generate_linkedin_post_updates_existing_draft(client, db_session):
    """Regenerate UPDATEs the existing draft row, does not INSERT a second row."""
    patent = PatentPublication(
        doc_id="USPTO:LP004",
        office="USPTO",
        publication_number="LP004",
        assignees=["UpdateCorp"],
        cpc=["G06N"],
        title="Update test patent",
        abstract="Testing upsert behavior on regenerate.",
        legal_status="GRANTED",
    )
    db_session.add(patent)
    await db_session.commit()

    artifact_id_1 = await _make_artifact(db_session)
    artifact_id_2 = await _make_artifact(db_session)

    fake_data_1 = {"post_markdown": "First generation.", "hook": "Hook 1", "tone": "analytical", "caveats": []}
    fake_data_2 = {"post_markdown": "Second generation.", "hook": "Hook 2", "tone": "curiosity", "caveats": []}

    from unittest.mock import AsyncMock, patch
    with patch("app.api.v1.content.generate_linkedin_post", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = (fake_data_1, artifact_id_1)
        await client.post("/api/v1/content/generate-linkedin", json={"patent_id": str(patent.id)})

    with patch("app.api.v1.content.generate_linkedin_post", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = (fake_data_2, artifact_id_2)
        await client.post("/api/v1/content/generate-linkedin", json={"patent_id": str(patent.id)})

    # Should be exactly 1 row, with the second generation's content
    result = await db_session.execute(
        select(ContentDraft).where(ContentDraft.source_id == patent.id)
    )
    drafts = result.scalars().all()
    assert len(drafts) == 1
    assert drafts[0].content_text == "Second generation."


@pytest.mark.asyncio
async def test_get_drafts_returns_existing(client, db_session):
    """GET /api/v1/content/drafts?patent_id=X returns the latest draft."""
    patent = PatentPublication(
        doc_id="USPTO:LP005",
        office="USPTO",
        publication_number="LP005",
        assignees=["GetCorp"],
        cpc=["B25J"],
        title="GET draft test",
        abstract="Testing draft retrieval endpoint.",
        legal_status="GRANTED",
    )
    db_session.add(patent)
    await db_session.commit()

    artifact_id = await _make_artifact(db_session)

    fake_data = {"post_markdown": "GET endpoint test.", "hook": "GET hook", "tone": "news", "caveats": []}

    from unittest.mock import AsyncMock, patch
    with patch("app.api.v1.content.generate_linkedin_post", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = (fake_data, artifact_id)
        await client.post("/api/v1/content/generate-linkedin", json={"patent_id": str(patent.id)})

    response = await client.get(f"/api/v1/content/drafts?patent_id={str(patent.id)}")
    assert response.status_code == 200
    body = response.json()
    assert body["post_markdown"] == "GET endpoint test."
    assert body["draft_id"] is not None
    assert body["source_citation"] is not None
    assert "LP005" in body["source_citation"]


@pytest.mark.asyncio
async def test_get_drafts_returns_none_for_unknown(client, db_session):
    """GET drafts for a patent with no drafts returns null."""
    fake_id = str(uuid4())
    response = await client.get(f"/api/v1/content/drafts?patent_id={fake_id}")
    assert response.status_code == 200
    assert response.json() is None
