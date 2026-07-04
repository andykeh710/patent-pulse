"""Tests for app.ai.tagger validation + payload building + cache flow."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.xfail(reason="KI-001: test DB schema incomplete — missing tables")

import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import llm_client as llm_module
from app.ai.llm_client import LLMClient
from app.ai.tagger import (
    OPPORTUNITY_TAG_VALUES,
    REQUIRED_TAG_FIELDS,
    RISK_FLAG_VALUES,
    build_tag_payload,
    validate_tags,
)
from app.ai.tagger import (
    tag_patent as cached_tag_patent,
)
from app.core.ai_models import AIArtifact
from app.core.exceptions import SummarizationError
from app.core.models import PatentPublication

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _valid_tag_response() -> dict:
    return {
        "industries": ["healthcare", "ai_ml"],
        "problem_solved": "Detecting anomalies in cardiac MRI scans.",
        "technology_method": ["machine_learning", "computer_vision"],
        "materials": [],
        "novel_application_categories": ["medical_device"],
        "time_horizon": "near_term",
        "risk_flags": ["regulatory_dependency"],
        "opportunity_tags": ["startup_opportunity"],
        "trend_tags": ["medical-imaging-edge-ai"],
    }


class TestBuildPayload:
    def test_payload_includes_assignees_and_cpc(self) -> None:
        p = PatentPublication(
            id=uuid4(),
            doc_id="USPTO:T001",
            office="USPTO",
            publication_number="T001",
            title="Cardiac anomaly detector",
            abstract="...",
            claims_text="1. A method ...",
            cpc=["G06N", "A61B"],
            assignees=["Acme Health"],
        )
        payload = build_tag_payload(p)
        assert "G06N" in payload["cpc_codes"]
        assert "Acme Health" in payload["assignees"]
        assert payload["title"] == "Cardiac anomaly detector"


class TestValidateTags:
    def test_accepts_valid_response(self) -> None:
        out = validate_tags(_valid_tag_response())
        assert out["time_horizon"] == "near_term"
        assert "machine_learning" in out["technology_method"]

    def test_lowercases_and_dedupes_lists(self) -> None:
        raw = _valid_tag_response()
        raw["industries"] = ["Healthcare", "healthcare", "AI_ML"]
        out = validate_tags(raw)
        assert out["industries"] == ["healthcare", "ai_ml"]

    def test_unknown_horizon_falls_back_to_unknown(self) -> None:
        raw = _valid_tag_response()
        raw["time_horizon"] = "yesterday"
        out = validate_tags(raw)
        assert out["time_horizon"] == "unknown"

    def test_missing_field_raises(self) -> None:
        raw = _valid_tag_response()
        del raw["risk_flags"]
        with pytest.raises(SummarizationError, match="missing required fields"):
            validate_tags(raw)

    def test_required_field_set(self) -> None:
        # Constants are wired through to the validator + frontend filters.
        assert "risk_flags" in REQUIRED_TAG_FIELDS
        assert "opportunity_tags" in REQUIRED_TAG_FIELDS
        assert len(OPPORTUNITY_TAG_VALUES) >= 5
        assert len(RISK_FLAG_VALUES) >= 5


# ---------------------------------------------------------------------------
# End-to-end: cached tag flow writes an AIArtifact(tags)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tag_patent_writes_artifact_via_cache(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p = PatentPublication(
        id=uuid4(),
        doc_id="USPTO:TAG001",
        office="USPTO",
        publication_number="TAG001",
        title="Test patent for tagging",
        abstract="A method for testing the tag pipeline end-to-end.",
        claims_text="1. A method comprising step X.",
        cpc=["G06F"],
        assignees=["Acme"],
    )
    db_session.add(p)
    await db_session.commit()

    # Fake Claude response: usage + JSON content.
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text=json.dumps(_valid_tag_response()))]
    fake_response.usage = MagicMock(input_tokens=300, output_tokens=200)
    anth = MagicMock()
    anth.messages.create.return_value = fake_response

    # Force the global llm client to use a fresh instance with our mock.
    client = LLMClient(api_key="test-key")
    monkeypatch.setattr(client, "_get_anthropic", lambda: anth)
    monkeypatch.setattr(llm_module, "_default_client", client)

    tags, artifact_id = await cached_tag_patent(db_session, p)
    assert tags["time_horizon"] == "near_term"
    assert "machine_learning" in tags["technology_method"]

    rows = (
        (
            await db_session.execute(
                select(AIArtifact)
                .where(AIArtifact.patent_publication_id == p.id)
                .where(AIArtifact.artifact_type == "tags")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].id == artifact_id
    assert rows[0].status == "complete"
    assert rows[0].input_tokens == 300

    # A second call with the same patent+prompt hits the cache → no new row.
    tags2, artifact_id2 = await cached_tag_patent(db_session, p)
    assert artifact_id2 == artifact_id
    rows2 = (
        (
            await db_session.execute(
                select(AIArtifact).where(AIArtifact.patent_publication_id == p.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows2) == 1
