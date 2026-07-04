"""Tests for the cached LLM client wrapper."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.xfail(reason="KI-001: test DB schema incomplete — missing ai_artifacts/users tables")
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import (
    LLMCacheMiss,
    LLMClient,
    LLMRequest,
    compute_input_hash,
    estimate_cost_usd,
    estimate_tokens,
)
from app.core.ai_models import AIArtifact
from app.core.models import PatentPublication

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestPricingHelpers:
    def test_estimate_tokens_zero_for_empty(self) -> None:
        assert estimate_tokens("") == 0
        assert estimate_tokens(None) == 0  # type: ignore[arg-type]

    def test_estimate_tokens_grows_with_chars(self) -> None:
        assert estimate_tokens("a" * 100) >= 25

    def test_cost_uses_per_million_pricing(self) -> None:
        cost = estimate_cost_usd(
            model="claude-sonnet-4-20250514",
            input_tokens=1_000_000,
            output_tokens=0,
        )
        # Sonnet input rate $3/Mtok by default.
        assert cost == pytest.approx(3.0, rel=0.01)

    def test_cost_haiku_cheaper_than_sonnet(self) -> None:
        sonnet = estimate_cost_usd(
            model="claude-sonnet-4-20250514",
            input_tokens=1_000_000,
            output_tokens=0,
        )
        haiku = estimate_cost_usd(
            model="claude-haiku-4-5",
            input_tokens=1_000_000,
            output_tokens=0,
        )
        assert haiku < sonnet


class TestInputHash:
    def test_hash_is_deterministic(self) -> None:
        h1 = compute_input_hash({"a": 1, "b": [2, 3]})
        h2 = compute_input_hash({"b": [2, 3], "a": 1})  # diff key order
        assert h1 == h2

    def test_hash_changes_on_payload_change(self) -> None:
        h1 = compute_input_hash({"a": 1})
        h2 = compute_input_hash({"a": 2})
        assert h1 != h2


# ---------------------------------------------------------------------------
# Cache lookup behavior
# ---------------------------------------------------------------------------


@pytest.fixture
async def patent_with_summary(db_session: AsyncSession) -> PatentPublication:
    p = PatentPublication(
        id=uuid4(),
        doc_id="USPTO:CACHE001",
        office="USPTO",
        publication_number="CACHE001",
        title="Cache test patent",
        abstract="Sample abstract for cache testing.",
        claims_text="1. A method comprising X.",
        cpc=["G06F"],
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.mark.asyncio
async def test_replay_mode_raises_on_cache_miss(
    db_session: AsyncSession, patent_with_summary: PatentPublication
) -> None:
    client = LLMClient(api_key="test-key", mode="replay")
    request = LLMRequest(
        artifact_type="summary",
        prompt_name="summarize",
        prompt_version=1,
        input_payload={"title": "x", "abstract": "y", "claims_text": "z",
                       "description_excerpt": "", "cpc_codes": "G06F"},
        patent_publication_id=patent_with_summary.id,
    )
    with pytest.raises(LLMCacheMiss):
        await client.complete(db_session, request)


@pytest.mark.asyncio
async def test_cache_hit_returns_existing_artifact(
    db_session: AsyncSession, patent_with_summary: PatentPublication
) -> None:
    """Pre-seed an AIArtifact and confirm the client returns it without API call."""
    from app.ai.prompts import get_prompt
    spec = get_prompt("summarize", 1)
    payload = {
        "title": "x",
        "abstract": "y",
        "claims_text": "z",
        "description_excerpt": "",
        "cpc_codes": "G06F",
    }
    input_hash = compute_input_hash(
        {"payload": payload, "subject_key": None, "model": "deepseek-v4-pro"}
    )
    artifact = AIArtifact(
        patent_publication_id=patent_with_summary.id,
        artifact_type="summary",
        artifact_version=1,
        model="claude-sonnet-4-20250514",
        prompt_name=spec.name,
        prompt_version=spec.version,
        prompt_hash=spec.prompt_hash,
        input_hash=input_hash,
        content_json={"what_it_is": "cached"},
        status="complete",
    )
    db_session.add(artifact)
    await db_session.commit()

    client = LLMClient(api_key="test-key", mode="replay")
    request = LLMRequest(
        artifact_type="summary",
        prompt_name="summarize",
        prompt_version=1,
        input_payload=payload,
        patent_publication_id=patent_with_summary.id,
    )
    response = await client.complete(db_session, request)
    assert response.cache_hit is True
    assert response.content_json == {"what_it_is": "cached"}


@pytest.mark.asyncio
async def test_record_mode_writes_artifact_on_success(
    db_session: AsyncSession, patent_with_summary: PatentPublication
) -> None:
    """Mock anthropic to return a JSON summary; expect an AIArtifact row."""
    fake_message = MagicMock()
    fake_message.content = [MagicMock(text='{"what_it_is": "live", "problem_solved":"x","how_it_works":"x","commercial_significance":"x","who_should_care":["x"],"novel_applications":[],"confidence_note":"x","source_spans":[]}')]
    fake_message.usage = MagicMock(input_tokens=200, output_tokens=300)

    client = LLMClient(api_key="test-key", mode="record")

    payload = {
        "title": "x", "abstract": "y", "claims_text": "z",
        "description_excerpt": "", "cpc_codes": "G06F",
    }
    request = LLMRequest(
        artifact_type="summary",
        prompt_name="summarize",
        prompt_version=1,
        input_payload=payload,
        patent_publication_id=patent_with_summary.id,
    )

    with patch.object(client, "_get_anthropic") as mock_get:
        mock_anth = MagicMock()
        mock_anth.messages.create.return_value = fake_message
        mock_get.return_value = mock_anth

        response = await client.complete(db_session, request)

    assert response.cache_hit is False
    assert response.content_json["what_it_is"] == "live"
    assert response.input_tokens == 200
    assert response.output_tokens == 300

    # AIArtifact row exists
    rows = (
        await db_session.execute(
            select(AIArtifact).where(AIArtifact.patent_publication_id == patent_with_summary.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "complete"
