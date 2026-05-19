"""
Unified LLM client wrapper.

Responsibilities
----------------
 1. **Caching.** Every completed call is recorded as an ``AIArtifact`` row
    keyed by ``(prompt_hash, input_hash, artifact_type)``. Subsequent calls
    with the same inputs short-circuit to the cached row.
 2. **Modes.** ``live`` always hits the API, ``record`` only on cache miss,
    ``replay`` never hits the API (raises on miss). Set via
    ``settings.llm_mode`` or per-call override.
 3. **Cost estimation + accounting.** ``estimate_cost()`` returns a USD
    estimate from input character counts + expected output. Actual cost is
    recorded on the artifact row using per-model pricing from ``settings``.
 4. **Per-model routing.** Callers request a logical tier ("summary",
    "tag", "narrative"); the client picks Sonnet or Haiku accordingly.
 5. **AIRun wiring.** If ``run_id`` is provided, the produced artifact is
    linked to the run and the run's counters are not updated here (the
    caller owns run lifecycle).

Contract
--------
All LLM access in the codebase is expected to flow through
:func:`complete`. Direct ``anthropic.Anthropic`` usage inside
``app/ai/*`` and ``app/tasks/*`` is being phased out as modules are
ported.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

import anthropic
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import get_prompt
from app.config import settings
from app.core.ai_models import AIArtifact

logger = logging.getLogger(__name__)

LLMMode = Literal["live", "record", "replay"]
ModelTier = Literal["summary", "tag", "narrative", "rerank", "embedding_only"]


class LLMCacheMiss(Exception):
    """Raised by ``complete()`` when mode=replay and no cache entry exists."""


class LLMBudgetExceeded(Exception):
    """Reserved for future per-run budget enforcement."""


# ---------------------------------------------------------------------------
# Pricing + token heuristics
# ---------------------------------------------------------------------------

# Rough heuristic: ~4 characters per token for English technical text.
# Used only for pre-flight estimation. Actual accounting uses the API's
# ``usage`` block.
CHARS_PER_TOKEN = 4.0


def _model_for_tier(tier: ModelTier) -> str:
    """Map logical tier → concrete Anthropic model id."""
    if tier in ("summary",):
        return settings.claude_model
    if tier in ("tag", "narrative", "rerank"):
        return settings.claude_haiku_model
    return settings.claude_haiku_model


def _pricing_for_model(model: str) -> tuple[float, float]:
    """Return (input_usd_per_mtok, output_usd_per_mtok) for a model."""
    m = (model or "").lower()
    if "sonnet" in m or "opus" in m:
        return (
            settings.claude_sonnet_input_usd_per_mtok,
            settings.claude_sonnet_output_usd_per_mtok,
        )
    # default to haiku pricing (safer-low for tags/narratives)
    return (
        settings.claude_haiku_input_usd_per_mtok,
        settings.claude_haiku_output_usd_per_mtok,
    )


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return int(math.ceil(len(text) / CHARS_PER_TOKEN))


def estimate_cost_usd(
    *, model: str, input_tokens: int, output_tokens: int
) -> float:
    in_rate, out_rate = _pricing_for_model(model)
    return round(
        (input_tokens / 1_000_000) * in_rate
        + (output_tokens / 1_000_000) * out_rate,
        6,
    )


# ---------------------------------------------------------------------------
# Input hashing
# ---------------------------------------------------------------------------


def compute_input_hash(payload: dict[str, Any]) -> str:
    """
    Deterministic hash over the caller-provided input payload.

    Callers should pass the fully-rendered prompt variables plus any
    ``subject_key`` so the cache key is stable across runs but specific to
    the exact input.
    """
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Request + response types
# ---------------------------------------------------------------------------


@dataclass
class LLMRequest:
    artifact_type: str
    prompt_name: str
    prompt_version: int
    input_payload: dict[str, Any]
    patent_publication_id: UUID | None = None
    subject_key: str | None = None
    run_id: UUID | None = None
    tier: ModelTier = "summary"
    max_tokens: int = 2048
    expected_output_tokens: int = 512
    mode: LLMMode | None = None
    # Optional override of the user-prompt string. When None, we render
    # ``spec.user_template.format(**input_payload)``.
    rendered_user_prompt: str | None = None
    extra_system: str | None = None


@dataclass
class LLMResponse:
    artifact_id: UUID
    artifact_type: str
    content_json: dict[str, Any] | None
    content_text: str | None
    model: str
    prompt_name: str
    prompt_version: int
    prompt_hash: str
    input_hash: str
    input_tokens: int
    output_tokens: int
    actual_cost_usd: float
    cache_hit: bool
    created_at: datetime
    # Full artifact row (useful for callers that want to denormalize).
    artifact: AIArtifact = field(repr=False)


# ---------------------------------------------------------------------------
# Core client
# ---------------------------------------------------------------------------


class LLMClient:
    """Wrapper around Anthropic with DB-backed content-addressed cache."""

    def __init__(
        self,
        api_key: str | None = None,
        mode: LLMMode | None = None,
    ):
        self._api_key = api_key if api_key is not None else settings.anthropic_api_key
        self._default_mode: LLMMode = mode or settings.llm_mode
        self._anthropic: anthropic.Anthropic | None = None

    # -- Anthropic client is lazy so replay-only flows never need a key. --

    def _get_anthropic(self) -> anthropic.Anthropic:
        if self._anthropic is None:
            if not self._api_key:
                raise RuntimeError(
                    "anthropic_api_key is not configured; cannot make live calls"
                )
            self._anthropic = anthropic.Anthropic(api_key=self._api_key)
        return self._anthropic

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(
        self, session: AsyncSession, request: LLMRequest
    ) -> LLMResponse:
        """Run an LLM call (or return cached artifact) and persist to DB."""
        spec = get_prompt(request.prompt_name, request.prompt_version)
        mode: LLMMode = request.mode or self._default_mode
        model = _model_for_tier(request.tier)

        input_hash = compute_input_hash(
            {
                "payload": request.input_payload,
                "subject_key": request.subject_key,
                "model": model,
            }
        )

        # ------------------------------------------------------------------
        # Cache lookup
        # ------------------------------------------------------------------
        cached = await self._find_cached(
            session=session,
            prompt_hash=spec.prompt_hash,
            input_hash=input_hash,
            artifact_type=request.artifact_type,
        )
        if cached is not None:
            logger.info(
                "LLM cache HIT",
                extra={
                    "artifact_type": request.artifact_type,
                    "prompt_hash": spec.prompt_hash[:12],
                    "input_hash": input_hash[:12],
                },
            )
            if request.run_id:
                cached = await self._record_run_cache_hit(
                    session=session,
                    request=request,
                    cached=cached,
                )
            return self._response_from_cache(cached)

        if mode == "replay":
            raise LLMCacheMiss(
                f"No cached artifact for type={request.artifact_type} "
                f"prompt_hash={spec.prompt_hash[:12]} input_hash={input_hash[:12]}"
            )

        # ------------------------------------------------------------------
        # Live call
        # ------------------------------------------------------------------
        user_prompt = (
            request.rendered_user_prompt
            if request.rendered_user_prompt is not None
            else _render_user_prompt(spec.user_template, request.input_payload, spec.schema_description)
        )
        system_prompt = spec.system
        if request.extra_system:
            system_prompt = f"{system_prompt}\n\n{request.extra_system}"

        client = self._get_anthropic()
        start = datetime.utcnow()
        try:
            message = await asyncio.to_thread(
                client.messages.create,
                model=model,
                max_tokens=request.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error for {request.artifact_type}: {e}")
            # Persist a failed artifact so callers can see the failure history.
            failed = AIArtifact(
                patent_publication_id=request.patent_publication_id,
                run_id=request.run_id,
                artifact_type=request.artifact_type,
                artifact_version=await self._next_artifact_version(
                    session=session,
                    artifact_type=request.artifact_type,
                    patent_publication_id=request.patent_publication_id,
                    subject_key=request.subject_key,
                ),
                model=model,
                prompt_name=spec.name,
                prompt_version=spec.version,
                prompt_hash=spec.prompt_hash,
                input_hash=input_hash,
                subject_key=request.subject_key,
                status="failed",
                error_message=str(e)[:4000],
            )
            session.add(failed)
            await session.commit()
            raise

        raw_text = message.content[0].text if message.content else ""
        usage = getattr(message, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
        actual_cost = estimate_cost_usd(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Attempt JSON parse; fall back to text-only storage.
        content_json: dict[str, Any] | None = None
        content_text: str | None = raw_text
        stripped = raw_text.strip()
        if stripped.startswith("{") or stripped.startswith("```"):
            try:
                content_json = _parse_json_loosely(stripped)
                content_text = None
            except (json.JSONDecodeError, ValueError):
                # Keep as text.
                content_json = None

        artifact = AIArtifact(
            patent_publication_id=request.patent_publication_id,
            run_id=request.run_id,
            artifact_type=request.artifact_type,
            artifact_version=await self._next_artifact_version(
                session=session,
                artifact_type=request.artifact_type,
                patent_publication_id=request.patent_publication_id,
                subject_key=request.subject_key,
            ),
            model=model,
            prompt_name=spec.name,
            prompt_version=spec.version,
            prompt_hash=spec.prompt_hash,
            input_hash=input_hash,
            subject_key=request.subject_key,
            content_json=content_json,
            content_text=content_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimate_cost_usd(
                model=model,
                input_tokens=estimate_tokens(system_prompt) + estimate_tokens(user_prompt),
                output_tokens=request.expected_output_tokens,
            ),
            actual_cost_usd=actual_cost,
            status="complete",
        )
        session.add(artifact)
        await session.commit()
        await session.refresh(artifact)
        elapsed = (datetime.utcnow() - start).total_seconds()
        logger.info(
            "LLM cache MISS -> live call",
            extra={
                "artifact_type": request.artifact_type,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "actual_cost_usd": actual_cost,
                "elapsed_s": round(elapsed, 2),
            },
        )
        return LLMResponse(
            artifact_id=artifact.id,
            artifact_type=artifact.artifact_type,
            content_json=artifact.content_json,
            content_text=artifact.content_text,
            model=artifact.model,
            prompt_name=artifact.prompt_name,
            prompt_version=artifact.prompt_version,
            prompt_hash=artifact.prompt_hash,
            input_hash=artifact.input_hash,
            input_tokens=artifact.input_tokens,
            output_tokens=artifact.output_tokens,
            actual_cost_usd=artifact.actual_cost_usd,
            cache_hit=False,
            created_at=artifact.created_at,
            artifact=artifact,
        )

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    async def _find_cached(
        self,
        *,
        session: AsyncSession,
        prompt_hash: str,
        input_hash: str,
        artifact_type: str,
    ) -> AIArtifact | None:
        stmt = (
            select(AIArtifact)
            .where(AIArtifact.prompt_hash == prompt_hash)
            .where(AIArtifact.input_hash == input_hash)
            .where(AIArtifact.artifact_type == artifact_type)
            .where(AIArtifact.status == "complete")
            .order_by(AIArtifact.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    def _response_from_cache(self, artifact: AIArtifact) -> LLMResponse:
        return LLMResponse(
            artifact_id=artifact.id,
            artifact_type=artifact.artifact_type,
            content_json=artifact.content_json,
            content_text=artifact.content_text,
            model=artifact.model,
            prompt_name=artifact.prompt_name,
            prompt_version=artifact.prompt_version,
            prompt_hash=artifact.prompt_hash,
            input_hash=artifact.input_hash,
            input_tokens=artifact.input_tokens,
            output_tokens=artifact.output_tokens,
            actual_cost_usd=artifact.actual_cost_usd,
            cache_hit=True,
            created_at=artifact.created_at,
            artifact=artifact,
        )

    async def _record_run_cache_hit(
        self,
        *,
        session: AsyncSession,
        request: LLMRequest,
        cached: AIArtifact,
    ) -> AIArtifact:
        marker_hash = compute_input_hash(
            {
                "cache_hit_artifact_id": cached.id,
                "run_id": request.run_id,
            }
        )
        existing = await self._find_cached(
            session=session,
            prompt_hash=cached.prompt_hash,
            input_hash=marker_hash,
            artifact_type=cached.artifact_type,
        )
        if existing is not None:
            return existing

        artifact = AIArtifact(
            patent_publication_id=cached.patent_publication_id,
            run_id=request.run_id,
            artifact_type=cached.artifact_type,
            artifact_version=await self._next_artifact_version(
                session=session,
                artifact_type=cached.artifact_type,
                patent_publication_id=cached.patent_publication_id,
                subject_key=cached.subject_key,
            ),
            model=cached.model,
            prompt_name=cached.prompt_name,
            prompt_version=cached.prompt_version,
            prompt_hash=cached.prompt_hash,
            input_hash=marker_hash,
            subject_key=cached.subject_key,
            content_json=cached.content_json,
            content_text=cached.content_text,
            input_tokens=0,
            output_tokens=0,
            estimated_cost_usd=0.0,
            actual_cost_usd=0.0,
            status="complete",
        )
        session.add(artifact)
        await session.commit()
        await session.refresh(artifact)
        return artifact

    async def _next_artifact_version(
        self,
        *,
        session: AsyncSession,
        artifact_type: str,
        patent_publication_id: UUID | None,
        subject_key: str | None,
    ) -> int:
        stmt = (
            select(AIArtifact.artifact_version)
            .where(AIArtifact.artifact_type == artifact_type)
            .order_by(AIArtifact.artifact_version.desc())
            .limit(1)
        )
        if patent_publication_id is not None:
            stmt = stmt.where(
                AIArtifact.patent_publication_id == patent_publication_id
            )
        elif subject_key is not None:
            stmt = stmt.where(AIArtifact.subject_key == subject_key)
        else:
            # Global artifact (rare); fall back to global max + 1.
            pass
        result = await session.execute(stmt)
        latest = result.scalar_one_or_none()
        return (latest or 0) + 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _render_user_prompt(
    template: str, payload: dict[str, Any], schema_description: str | None
) -> str:
    """Render the user prompt with payload + optional schema placeholder."""
    merged = dict(payload)
    if "schema_description" not in merged:
        merged["schema_description"] = schema_description or ""
    return template.format(**merged)


def _parse_json_loosely(text: str) -> dict[str, Any]:
    """Parse a JSON response tolerant of ```json``` fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------


_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


# ---------------------------------------------------------------------------
# Rules-artifact helper (no-LLM path)
# ---------------------------------------------------------------------------


@dataclass
class RulesArtifactRequest:
    """A rules-based per-patent computation that should be cached.

    The ``rules_id`` + ``rules_version`` pair becomes the artifact's
    ``prompt_name`` + ``prompt_version``; their hash becomes ``prompt_hash``.
    Together with ``input_payload`` (the patent feature fingerprint) they
    form the cache key. ``content_json`` is the deterministic output of
    running the rules over ``input_payload``.
    """

    artifact_type: str
    rules_id: str
    rules_version: int
    rules_hash: str  # hash of (formula version + weights dict)
    input_payload: dict[str, Any]
    content_json: dict[str, Any]
    patent_publication_id: UUID | None = None
    subject_key: str | None = None
    run_id: UUID | None = None


async def record_rules_artifact(
    session: AsyncSession, request: RulesArtifactRequest
) -> LLMResponse:
    """Cache-or-create an AIArtifact from a deterministic rules output.

    Mirrors :meth:`LLMClient.complete` semantics but never calls an LLM.
    Returns the same :class:`LLMResponse` shape (with ``model='rules:v<n>'``,
    zero token counts, zero cost) so callers can treat both paths uniformly.
    """
    input_hash = compute_input_hash(
        {
            "payload": request.input_payload,
            "subject_key": request.subject_key,
            "model": f"rules:v{request.rules_version}",
        }
    )

    # Cache lookup using the same triple as LLM artifacts.
    cached_stmt = (
        select(AIArtifact)
        .where(AIArtifact.prompt_hash == request.rules_hash)
        .where(AIArtifact.input_hash == input_hash)
        .where(AIArtifact.artifact_type == request.artifact_type)
        .where(AIArtifact.status == "complete")
        .order_by(AIArtifact.created_at.desc())
        .limit(1)
    )
    cached = (await session.execute(cached_stmt)).scalar_one_or_none()
    if cached is not None:
        logger.info(
            "rules artifact cache HIT",
            extra={
                "artifact_type": request.artifact_type,
                "rules_id": request.rules_id,
                "rules_version": request.rules_version,
            },
        )
        if request.run_id:
            marker_hash = compute_input_hash(
                {
                    "cache_hit_artifact_id": cached.id,
                    "run_id": request.run_id,
                }
            )
            marker_stmt = (
                select(AIArtifact)
                .where(AIArtifact.prompt_hash == cached.prompt_hash)
                .where(AIArtifact.input_hash == marker_hash)
                .where(AIArtifact.artifact_type == cached.artifact_type)
                .where(AIArtifact.status == "complete")
                .limit(1)
            )
            marker = (await session.execute(marker_stmt)).scalar_one_or_none()
            if marker is None:
                marker = AIArtifact(
                    patent_publication_id=cached.patent_publication_id,
                    run_id=request.run_id,
                    artifact_type=cached.artifact_type,
                    artifact_version=await _next_rules_artifact_version(
                        session=session,
                        artifact_type=cached.artifact_type,
                        patent_publication_id=cached.patent_publication_id,
                        subject_key=cached.subject_key,
                    ),
                    model=cached.model,
                    prompt_name=cached.prompt_name,
                    prompt_version=cached.prompt_version,
                    prompt_hash=cached.prompt_hash,
                    input_hash=marker_hash,
                    subject_key=cached.subject_key,
                    content_json=cached.content_json,
                    content_text=cached.content_text,
                    input_tokens=0,
                    output_tokens=0,
                    estimated_cost_usd=0.0,
                    actual_cost_usd=0.0,
                    status="complete",
                )
                session.add(marker)
                await session.commit()
                await session.refresh(marker)
            cached = marker
        return LLMResponse(
            artifact_id=cached.id,
            artifact_type=cached.artifact_type,
            content_json=cached.content_json,
            content_text=cached.content_text,
            model=cached.model,
            prompt_name=cached.prompt_name,
            prompt_version=cached.prompt_version,
            prompt_hash=cached.prompt_hash,
            input_hash=cached.input_hash,
            input_tokens=0,
            output_tokens=0,
            actual_cost_usd=0.0,
            cache_hit=True,
            created_at=cached.created_at,
            artifact=cached,
        )

    # Compute next version per (artifact_type, subject).
    version_stmt = (
        select(AIArtifact.artifact_version)
        .where(AIArtifact.artifact_type == request.artifact_type)
        .order_by(AIArtifact.artifact_version.desc())
        .limit(1)
    )
    if request.patent_publication_id is not None:
        version_stmt = version_stmt.where(
            AIArtifact.patent_publication_id == request.patent_publication_id
        )
    elif request.subject_key is not None:
        version_stmt = version_stmt.where(
            AIArtifact.subject_key == request.subject_key
        )
    latest = (await session.execute(version_stmt)).scalar_one_or_none()
    next_version = (latest or 0) + 1

    artifact = AIArtifact(
        patent_publication_id=request.patent_publication_id,
        run_id=request.run_id,
        artifact_type=request.artifact_type,
        artifact_version=next_version,
        model=f"rules:v{request.rules_version}",
        prompt_name=request.rules_id,
        prompt_version=request.rules_version,
        prompt_hash=request.rules_hash,
        input_hash=input_hash,
        subject_key=request.subject_key,
        content_json=request.content_json,
        content_text=None,
        input_tokens=0,
        output_tokens=0,
        estimated_cost_usd=0.0,
        actual_cost_usd=0.0,
        status="complete",
    )
    session.add(artifact)
    await session.flush()
    await session.refresh(artifact)
    logger.info(
        "rules artifact recorded",
        extra={
            "artifact_type": request.artifact_type,
            "rules_id": request.rules_id,
            "rules_version": request.rules_version,
            "version": next_version,
        },
    )
    return LLMResponse(
        artifact_id=artifact.id,
        artifact_type=artifact.artifact_type,
        content_json=artifact.content_json,
        content_text=None,
        model=artifact.model,
        prompt_name=artifact.prompt_name,
        prompt_version=artifact.prompt_version,
        prompt_hash=artifact.prompt_hash,
        input_hash=artifact.input_hash,
        input_tokens=0,
        output_tokens=0,
        actual_cost_usd=0.0,
        cache_hit=False,
        created_at=artifact.created_at,
        artifact=artifact,
    )


async def _next_rules_artifact_version(
    *,
    session: AsyncSession,
    artifact_type: str,
    patent_publication_id: UUID | None,
    subject_key: str | None,
) -> int:
    version_stmt = (
        select(AIArtifact.artifact_version)
        .where(AIArtifact.artifact_type == artifact_type)
        .order_by(AIArtifact.artifact_version.desc())
        .limit(1)
    )
    if patent_publication_id is not None:
        version_stmt = version_stmt.where(
            AIArtifact.patent_publication_id == patent_publication_id
        )
    elif subject_key is not None:
        version_stmt = version_stmt.where(AIArtifact.subject_key == subject_key)
    latest = (await session.execute(version_stmt)).scalar_one_or_none()
    return (latest or 0) + 1


def hash_rules(rules_id: str, version: int, payload: dict[str, Any]) -> str:
    """Stable hash for rules implementation + weights. Used as ``prompt_hash``.

    Bumping ``version`` or any weight invalidates every prior cached artifact
    for that rules family and forces recompute on next access.
    """
    encoded = json.dumps(
        {"rules_id": rules_id, "version": version, "payload": payload},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
