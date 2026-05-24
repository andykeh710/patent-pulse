# Sprint 5 — Commercial Usage Signals MVP: Implementation Plan

> **Scope doc:** `.hermes/plans/2026-05-22_sprint-5-usage-signals-scope.md`
> (updated 2026-05-23 with 12 decisions from scope review)

## Build Order (9 sections)

### 1. Migration — `usage_evidence` + `patent_usage_signals`

**Purpose:** Create both tables per the scope doc schema (lines 145-234).

**Files:**
- `backend/alembic/versions/0011_add_usage_signals_tables.py`
- `backend/app/core/ai_models.py` — add `UsageEvidence` + `PatentUsageSignals` ORM models

**Acceptance criteria:**
- `alembic upgrade head` applies cleanly from 0010
- Both model classes importable, all column types correct
- Foreign keys cascade on delete
- Indexes created as specified

---

### 2. Evidence Collectors

**Purpose:** Two collector modules — one per MVP evidence source. No LLM.

#### 2a — Forward Citation Collector

**File:** `backend/app/usage/citation_collector.py`

Collects forward-citation evidence from `PatentPublication.citations_forward`.

```python
async def collect_citation_evidence(session, patent_id) -> list[dict]:
    patent = await get(PatentPublication, patent_id)
    if not patent.citations_forward:
        return []
    # For each forward citation, look up the source patent.
    # Compute tier based on recency + CPC overlap.
    # Return list of evidence dicts ready for insertion.
```

**Tier assignment:** strong (≤5yr + ≥2 shared CPC), medium (≤10yr), weak (>10yr or self-citation), excluded (>20yr).

#### 2b — Similar Patent Collector

**File:** `backend/app/usage/similarity_collector.py`

Uses `pgvector` `<=>` operator to find semantically similar patents filed AFTER the target.

```python
async def collect_similar_evidence(session, patent_id) -> list[dict]:
    # Filter to patents with filing_date > target.grant_date (or filing_date).
    # Compute tier based on similarity + CPC overlap.
    # Cap at 10 results.
```

**Tier assignment:** strong (≥0.85 + ≥1 shared CPC), medium (≥0.75), weak (≥0.65), excluded (<0.65).

**Performance gate:** Measure kNN query time on 50K corpus BEFORE backfill. If >1s, batch in worker.

#### 2c — Orchestrator

**File:** `backend/app/usage/collector.py`

```python
async def collect_all_evidence(session, patent_id) -> tuple[list, list]:
    citations = await collect_citation_evidence(session, patent_id)
    similar = await collect_similar_evidence(session, patent_id)
    # Dedup by source_patent_id — keep higher tier.
    merged = dedup_evidence(citations, similar)
    return merged, stats
```

**Acceptance criteria (section 2):**
- Each collector independently testable with a patent that has forward citations
- Similar collector handles patent without embeddings (returns [])
- Dedup works when same patent appears in both sources
- Self-citations detected and flagged

---

### 3. Scoring Engine

**Purpose:** Deterministic scoring + aggregate row population.

**File:** `backend/app/usage/scorer.py`

```python
def compute_usage_signal_score(evidence_rows: list) -> dict:
    # evidence_strength: strong=10, medium=5, weak=2 per piece, cap 40
    # recency: based on most recent evidence date
    # diversity: 2+ sources = 15, single = 8
    # assignee_activity: distinct assignees count → score
    # cpc_overlap: average shared CPC count → score
    # Apply anti-gaming: self-citation × 1/3, same-assignee-similar × 1/2
    # Return {score, confidence, breakdown, market_categories, top_companies, ...}
```

**Acceptance criteria:**
- Score 0 when no evidence
- Score increases with more + stronger evidence
- Self-citation penalty reduces score
- Score 100 achievable only with multiple strong diverse recent evidence
- Breakdown dict shows all component scores

---

### 4. AI Narrative Module

**Purpose:** LLM-generated narrative for medium+ confidence patents. Mirrors
`trend_narrative.py` pattern: on-demand, AIArtifact cache, `validate_output`.

**Files:**
- `backend/app/ai/usage_narrative.py` — `build_payload`, `validate_output`, `generate_usage_narrative`
- `backend/app/ai/prompts/usage_signal_narrative_v1.md` — SYSTEM/SCHEMA/USER

**Tier:** `"summary"` (Sonnet). Matches trend_narrative. Haiku produced
unstable JSON envelopes on structured narrative schemas in Sprint 4
diagnosis. Cost: ~$0.003/narrative, trivial at 15k scale ($45 total).

**Anti-pattern enforcement:** validate_output checks for forbidden phrases
in output. If any forbidden phrase found, request regeneration (max 2 retries).

**Cache invalidation:** Don't auto-invalidate. Show "stale — evidence recomputed
[DATE]" on frontend if `narrative_generated_at < patent_usage_signals.updated_at`.

**Acceptance criteria:**
- On-demand generation via `POST /api/v1/signals/{id}/narrative`
- Cache hit returns same result (verified via test)
- Forbidden phrase detection in validate_output
- Tier: "summary" (Sonnet, ~$0.003/narrative)
- Prompt includes evidence list with tiers, patent metadata, explicit
  anti-overclaim rules

---

### 5. Backfill Task

**Purpose:** Populate evidence + signals for all patents.

**File:** `backend/app/tasks/backfill_usage_signals.py`

```python
async def backfill_usage_signals_for_session(session, *, limit=None) -> dict:
    # 1. SELECT patents ordered by opportunity_score DESC (prioritize high-value)
    # 2. For each: collect evidence → score → upsert patent_usage_signals
    # 3. Insert usage_evidence rows (caps at 50 per patent)
    # 4. Return stats: processed, scored, skipped, errors
```

Wrapper calls `async_session_maker` (production). Session-aware variant (testable).

**Acceptance criteria:**
- Idempotent — second run updates existing rows, doesn't duplicate
- Caps evidence at 50 rows per patent
- Logs per-patent stats at INFO level
- Respects limit parameter for batch processing

---

### 6. API Endpoints

**Files:**
- `backend/app/api/v1/signals.py` — new router
- `backend/app/api/v1/router.py` — register router

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/signals/{patent_id}` | Get usage signal summary for a patent (from `patent_usage_signals`) |
| GET | `/api/v1/signals/{patent_id}/evidence` | List evidence rows for a patent |
| POST | `/api/v1/signals/{patent_id}/narrative` | Generate/cache usage narrative |
| GET | `/api/v1/signals/{patent_id}/narrative` | Fetch cached narrative |

**Schemas:** Mirror `TrendNarrativeResponse` pattern, add `UsageSignalResponse`,
`UsageEvidenceItem`.

**Acceptance criteria:**
- GET signal returns null when no assessment done
- GET evidence returns empty when no evidence (never 404)
- POST narrative returns 400 if score < 40
- GET narrative returns null when no cache

---

### 7. Frontend — Usage Signals Tab

**Files:**
- `frontend/src/components/patents/UsageSignalsPanel.tsx`
- `frontend/src/app/patents/[id]/page.tsx` — add 8th tab

**Panel content (when evidence exists):**
- Score badge (0-100, color-coded: green ≥70, amber 40-69, gray <40)
- Confidence label
- Evidence list (expandable, tier-badged)
- Self-citation warning if flag true
- "Analyze" button for narrative (score ≥40 only)
- Narrative display with AISourceFooter + stale indicator
- Mandatory disclaimer footer

**Panel content (no evidence):**
- "No Usage Signals Detected"
- "Checked X forward citations and Y similar newer patents"
- Legal-context explanation
- Links to citations tab and similar patents tab

**Reuse:** AISourceFooter, Badge, Skeleton, EmptyState patterns.

**Acceptance criteria:**
- Renders for patent with signals (after backfill)
- Renders empty state for patent without signals
- Narrative generates and caches correctly
- Self-citation badge appears when flag set
- No forbidden language anywhere

---

### 8. Expiry Radar Integration

**Files:**
- `frontend/src/components/expiry/ExpiryRadarCard.tsx` — replace "0" placeholder
- `backend/app/api/v1/expiry.py` — add `has_usage_signals` filter

**Frontend changes:**
- Fetch `usage_signal_score` via a bulk endpoint or per-card fetch
- If no data: show "Usage signals assessed — check patent detail" tooltip
- If data: show real score badge + confidence dot
- Self-citation badge in card footer

**Backend changes:**
- LEFT JOIN `patent_usage_signals` in expiry list query
- Add `has_usage_signals` boolean filter (true = has row, false = no row)
- Add `usage_signal_score` to ExpiryItem response schema

**Acceptance criteria:**
- "0" placeholder replaced throughout
- Filter respects join (tests verify)
- Score appears when data exists, empty state when not

---

### 9. Tests

**Files:**
- `backend/tests/usage/test_collectors.py` — collector unit tests
- `backend/tests/usage/test_scorer.py` — scoring unit tests
- `backend/tests/usage/test_narrative.py` — narrative unit tests
- `backend/tests/api/test_signals.py` — API endpoint tests

**Minimum test coverage:**

| Test | What it verifies |
|------|-----------------|
| Citation collector: no forward citations → [] | Empty handling |
| Citation collector: self-citation flagged | Anti-gaming |
| Citation collector: tier assignment by age | Classification |
| Similar collector: no embedding → [] | Empty handling |
| Similar collector: tier by similarity | Classification |
| Similar collector: older patents excluded | "Newer" filter |
| Dedup: same patent in both → one row | Dedup logic |
| Scorer: 0 evidence → 0 score | Floor |
| Scorer: 3 strong recent → high score | Ceiling |
| Scorer: self-citation penalty applied | Anti-gaming |
| Narrative: forbidden phrase rejected | Language guard |
| Narrative: cache hit returns same result | Caching |
| API: GET signal returns null before backfill | Initial state |
| API: POST narrative 400 if score < 40 | Threshold |
| Expiry filter: has_usage_signals respects join | Filter |

**Acceptance criteria:**
- Full `pytest -q` (no --ignore) — count reported vs baseline
- 0 failed, 0 warnings in usage-specific test modules
- Language audit: `grep -rE "free to use|public domain|is used by" backend/app/usage/ backend/app/ai/usage_narrative.py frontend/src/components/patents/UsageSignalsPanel.tsx` returns zero

---

## Files Summary

| Created | Modified |
|---------|----------|
| `backend/alembic/versions/0011_*.py` | `backend/app/core/ai_models.py` |
| `backend/app/usage/__init__.py` | `backend/app/api/v1/router.py` |
| `backend/app/usage/citation_collector.py` | `backend/app/api/v1/expiry.py` |
| `backend/app/usage/similarity_collector.py` | `frontend/src/app/patents/[id]/page.tsx` |
| `backend/app/usage/collector.py` | `frontend/src/components/expiry/ExpiryRadarCard.tsx` |
| `backend/app/usage/scorer.py` | `frontend/src/lib/types.ts` |
| `backend/app/ai/usage_narrative.py` | `frontend/src/lib/api.ts` |
| `backend/app/ai/prompts/usage_signal_narrative_v1.md` | |
| `backend/app/api/v1/signals.py` | |
| `backend/app/tasks/backfill_usage_signals.py` | |
| `backend/tests/usage/test_*.py` × 3 | |
| `backend/tests/api/test_signals.py` | |
| `frontend/src/components/patents/UsageSignalsPanel.tsx` | |

## Language Audit (mandatory before declaring done)

Before commit, run:
```
grep -rE "free to use|public domain|is used by|has been adopted|being commercialized|can freely use|safe to build|no licensing required" backend/app/usage/ backend/app/ai/usage_narrative.py backend/app/ai/prompts/usage_signal_narrative_v1.md frontend/src/components/patents/UsageSignalsPanel.tsx
```

Zero hits required in user-facing content. Test strings OK.

## Reporting Rules (carried forward)

- Full `pytest -q` — no `--ignore`. Report exact count vs baseline.
- Every verification: exact coverage numbers, quantifier on every ✅.
- Every deviation: DEVIATION DETECTED with A/B/C options.
- Language audit must include narrative output samples.
