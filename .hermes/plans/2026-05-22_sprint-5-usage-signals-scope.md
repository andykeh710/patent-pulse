# Sprint 5 — Commercial Usage Signals: Scope Document

> **Status:** Design/scoping pass. No implementation plan yet. Debate scope before
> committing to an implementation plan.

## 1. Evidence Sources — MVP vs Deferred

Commercial usage signals answer: "This patent is expired or expiring. Are
similar ideas showing up in current products, companies, or newer patents?"

Evidence comes from many sources. The MVP constraint is: **use data we
already have or can compute cheaply.** No web scraping in V1.

| Source | MVP? | Rationale |
|--------|------|-----------|
| Forward citations | ✅ **MVP** | Forward citations already in DB (`citations_forward` column, migration 0009). Deterministic, zero cost per patent, always fresh. |
| Semantically similar newer patents | ✅ **MVP** | Existing embeddings via `pgvector`. Call `semanticApi.similar()` filtered to newer patents. Cheap batch computation. |
| Company product pages | ❌ Defer | Requires web scraping or API integration. Fragile, high maintenance, legal grey area. Defer to v2. |
| Press releases | ❌ Defer | Same as product pages — scraping required, stale quickly. |
| Technical articles | ❌ Defer | ArXiv/CrossRef APIs exist but coverage is spotty for patent-article matching. |
| Marketplace listings | ❌ Defer | Amazon, Etsy, etc. — no stable API for patent matching. High false-positive risk. |
| Standards documents | ❌ Defer | WIPO/ITU/IEEE standards have APIs but patent-standard matching is a research problem. |
| Open-source repo references | ❌ Defer | GitHub search API exists but patent-repo matching requires named entity recognition. |

**MVP decision:** Forward citations + semantically similar newer patents
only. This gives real, verifiable evidence at zero incremental cost per
patent. Other sources are post-MVP, gated on user demand and cost analysis.

## 2. Confidence Tiering

Every piece of evidence is assigned a confidence tier. The tier determines
how strongly we present it.

### Tier 1 — Strong

Evidence that directly connects this patent to current technology.

| Source | Strong criteria |
|--------|----------------|
| Forward citation | A patent filed in the last **5 years** cites this patent **and** shares ≥2 CPC codes. |
| Similar newer patent | A patent filed after this patent's grant date has **≥0.85 cosine similarity** on embeddings **and** shares ≥1 CPC code. |

### Tier 2 — Medium

Evidence that suggests relevance but lacks direct linkage.

| Source | Medium criteria |
|--------|----------------|
| Forward citation | A patent filed in the last **10 years** cites this patent but shares **0-1** CPC codes. |
| Similar newer patent | A patent filed after the grant date has **≥0.75 cosine similarity** but different CPC sections. |

### Tier 3 — Weak

Evidence that is directionally interesting but should not be presented
as a strong signal.

| Source | Weak criteria |
|--------|---------------|
| Forward citation | Older than 10 years, or self-citation by the same assignee. |
| Similar newer patent | Similarity **≥0.65** but different CPC and different assignee. |

### Exclusion threshold

Evidence below these thresholds is **not stored**:
- Forward citations older than 20 years (expired prior art, not current usage)
- Semantic similarity below 0.65
- Self-citations by the same assignee on patents older than 10 years

### Evidence dedup

When a source patent appears in BOTH forward citations AND similar
patents, count it once at the higher tier. Dedup by `source_patent_id`.
This prevents double-counting a patent that both cites and is
semantically similar.

### "Newer patent" definition

For similar-patent evidence, "newer" means: `source.filing_date >
target.grant_date` (preferred). Fallback: `source.filing_date >
target.filing_date` when `grant_date` is null on the target patent.
This ensures we only match against patents filed AFTER the target
was known.

## 3. Scoring Formula

`usage_signal_score` lives on `patent_usage_signals`. Range: 0–100.
Deterministic, not LLM. Mirrors the structure of `expiry_opportunity_score`.

### Components

| Component | Weight | Range | Description |
|-----------|--------|-------|-------------|
| `evidence_strength` | 0.40 | 0–40 | Weighted sum of evidence by tier: strong=10pts, medium=5pts, weak=2pts per piece, capped at 40 |
| `recency` | 0.25 | 0–25 | How recent is the strongest evidence: ≤2yr=25, ≤5yr=18, ≤10yr=10, >10yr=0 |
| `diversity` | 0.15 | 0–15 | Evidence from multiple sources (citations AND similar patents) = 15; single source = 8 |
| `assignee_activity` | 0.10 | 0–10 | ≥3 different assignees in evidence = 10; ≥2 = 6; 1 = 3; 0 = 0 |
| `cpc_overlap` | 0.10 | 0–10 | Average CPC overlap between source patent and evidence: ≥3 shared = 10; 2 = 7; 1 = 4; 0 = 0 |

### Formula

```
raw_score = evidence_strength + recency + diversity + assignee_activity + cpc_overlap
usage_signal_score = clamp(0, 100, raw_score)
```

### Confidence labels (derived from score, not separate)

| Score range | Label stored (VARCHAR 8) | Display label |
|-------------|--------------------------|---------------|
| ≥ 70 | "high" | High |
| 40–69 | "medium" | Medium |
| 20–39 | "low" | Low |
| < 20 | "low" | Insufficient evidence |

Note: column is VARCHAR(8). "insufficient" (12 chars) doesn't fit.
Frontend displays "Insufficient evidence" when score < 20 based on
score value, not the stored label. Documented 2026-05-23.

### anti-gaming guard

- Self-citations (same assignee citing itself) are counted at 1/3 weight.
- Similar patents from the same assignee are counted at 1/2 weight.
- Evidence older than 15 years does not contribute to `recency`.

## 4. Language Rules — Allowed vs Forbidden

From `AGENTS.md`, expanded with concrete examples.

### Forbidden phrases (never use)

- "This patent is used in Product X."
- "Company Y uses this technology."
- "This invention is currently in production."
- "This expired patent is being commercialized by..."
- "Evidence confirms that..."
- "You can freely use this patent."
- "This patent is public domain."
- "Safe to build on this."
- "No licensing required."

### Allowed phrases (by confidence tier)

**Strong evidence:**
- "Recent patents in related technology areas cite this invention, suggesting ongoing relevance."
- "Multiple newer patents show technical overlap with the mechanisms disclosed here."
- "Several companies are filing in closely related CPC areas using similar approaches."

**Medium evidence:**
- "This invention appears related to technologies described in newer patent filings."
- "The technical mechanisms disclosed here show overlap with recent innovations in [CPC area]."
- "Related technology continues to appear in patent activity from [N] assignees."

**Weak evidence:**
- "Limited patent activity suggests possible continued relevance in [area]."
- "A small number of newer patents reference similar approaches."
- "This technology area has seen some continued filing activity."

**Always append (on every signal panel):**
- "These signals are evidence-backed hypotheses, not confirmation of commercial use. Verify independently before making business or legal decisions."
- "Evidence is sourced from patent citations and semantic similarity. It does not include product-level verification."

## 5. Database Design

### `usage_evidence`

One row per piece of evidence. Multiple rows point to one patent.

```sql
CREATE TABLE usage_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patent_publication_id UUID NOT NULL
        REFERENCES patent_publications(id) ON DELETE CASCADE,

    -- What kind of evidence
    source_type VARCHAR(32) NOT NULL,
        -- 'forward_citation' | 'similar_newer_patent'

    -- The evidence itself
    source_patent_id UUID
        REFERENCES patent_publications(id) ON DELETE SET NULL,
    source_patent_doc_id VARCHAR(64),
    source_patent_title TEXT,
    source_patent_assignee TEXT,
    source_patent_filing_date DATE,
    source_patent_cpc JSONB DEFAULT '[]',

    -- Matching metadata
    matched_cpc TEXT[],              -- CPC codes shared between source and target
    cpc_overlap_count INTEGER DEFAULT 0,
    similarity_score FLOAT,           -- only for similar_newer_patent
    citation_direction VARCHAR(16),   -- 'forward' | 'backward' — only for forward_citation

    -- Classification
    evidence_tier VARCHAR(8) NOT NULL,  -- 'strong' | 'medium' | 'weak'
    evidence_confidence FLOAT NOT NULL DEFAULT 0.0,  -- 0.0–1.0

    -- Timestamps
    retrieved_at TIMESTAMP NOT NULL DEFAULT now(),

    -- Indexes
    INDEX ix_usage_evidence_patent (patent_publication_id),
    INDEX ix_usage_evidence_tier (evidence_tier),
    INDEX ix_usage_evidence_source_type (source_type),
    INDEX ix_usage_evidence_source_patent (source_patent_id)
);
```

### `patent_usage_signals`

One row per assessed patent. Aggregates evidence into a score + summary.

```sql
CREATE TABLE patent_usage_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patent_publication_id UUID NOT NULL UNIQUE
        REFERENCES patent_publications(id) ON DELETE CASCADE,

    -- Score
    usage_signal_score FLOAT,           -- 0–100
    usage_signal_confidence VARCHAR(8),  -- 'high' | 'medium' | 'low'
    score_breakdown JSONB,              -- component scores (see §3)

    -- Aggregates
    evidence_count INTEGER DEFAULT 0,
    strong_evidence_count INTEGER DEFAULT 0,
    medium_evidence_count INTEGER DEFAULT 0,
    weak_evidence_count INTEGER DEFAULT 0,
    strongest_evidence_ids UUID[],      -- top 3 evidence IDs for the UI

    -- Derived fields (for filtering/sorting, no LLM)
    market_categories TEXT[],           -- CPC sections/tags from evidence
    top_companies TEXT[],               -- most frequent assignees in evidence
    most_recent_evidence_date DATE,

    -- Narrative (optional, added by LLM pass — see §7)
    narrative_summary TEXT,
    narrative_artifact_id UUID
        REFERENCES ai_artifacts(id) ON DELETE SET NULL,
    narrative_generated_at TIMESTAMP,

    -- Flags
    has_self_citation_risk BOOLEAN DEFAULT false,
    has_stale_evidence_risk BOOLEAN DEFAULT false,

    -- Timestamps
    computed_at TIMESTAMP NOT NULL DEFAULT now(),

    -- Indexes
    INDEX ix_usage_signals_patent (patent_publication_id),
    INDEX ix_usage_signals_score (usage_signal_score),
    INDEX ix_usage_signals_confidence (usage_signal_confidence)
);
```

## 6. UI Surface

### Patent detail page — new "Usage Signals" tab (8th tab)

Placement: new tab **"Usage Signals"** after Legal/Expiry. Resolved
2026-05-23: dedicated tab, not a panel inside Opportunity.

Even with zero evidence, the tab renders with the empty state below
(never hidden — hidden tabs look broken).

Empty state:
```
No Usage Signals Detected
─────────────────────────
Checked X forward citations and Y similar newer patents.
No evidence met the significance threshold (≥0.65 similarity
and/or shared CPC code). This does not mean the technology is
unused — evidence is patent-based only. Product-level usage
is not tracked.

[View patent citations →] [View similar patents →]
```

Panel content (when evidence exists):

```
Commercial Usage Signals
Score: 72/100 (High confidence)
─────────────────────────────────
This expired patent's technology appears related to current patent
activity. 8 pieces of evidence found.

[Evidence list — expandable]
├─ US2024/0123456  (forward citation, strong)
│  "A method for..."  CPC: G06F, H04L
│  Filed 2024 · Acme Corp
├─ US2023/0789012  (similar patent, strong)
│  87% similarity · 3 CPC codes shared
│  Filed 2023 · Beta Inc
├─ ... (6 more)

Limitations:
• Evidence is patent-based only — no product-level verification.
• Self-citations have been downweighted.
• Verify independently before business decisions.
```

### Expiry Radar — filter + column

- New filter: `has_usage_signals=true/false`
- New sort: `usage_signal_score` (asc/desc)
- New column on ExpiryRadarCard: score badge + confidence dot
- Existing "0" placeholder replaced with empty-state-or-real-data:
  (a) Sprint 5 "Usage signals assessed — check patent detail" if no data,
  (b) real score badge + count when backfill populates data
- **Self-citation badge:** when `has_self_citation_risk` is true, show:
  "⚠ Self-citation risk: N of M evidence pieces share an assignee with
  the source patent."

### Does NOT appear elsewhere in MVP

- No dashboard card (needs aggregation — Sprint 6)
- No newsletter section (Sprint 6)
- No alert trigger (Sprint 6)

## 7. AI Narrative

An LLM can generate a 2-3 sentence narrative summarizing the evidence.
This is optional — the deterministic score + evidence list is the core
product. The narrative is for users who want a quick read.

### When to generate

On-demand via user clicking "Analyze" on the Usage Signals tab. Mirrors
the trend_narrative pattern (Sprint 4): `POST /api/v1/signals/{id}/narrative`
generates and caches via AIArtifact. Cache hit returns cached result.

Only generate when `usage_signal_score ≥ 40` (medium+ confidence). Below
that, evidence too thin for meaningful narrative — show "Not enough
evidence for narrative generation" with the empty state.

### Prompt outline

```
# SYSTEM
You summarize patent usage signal evidence. Your output is read by
founders, investors, and R&D scouts. You must be accurate and cautious.

Rules:
- Summarize ONLY the evidence provided. Do not add information.
- Never claim a product uses this patent.
- Never claim a company is commercializing this technology.
- Use hedging language: "appears related to," "shows overlap with,"
  "suggests continued relevance in."
- Cite specific evidence pieces by ID.
- If evidence is thin, say so.
- Include at least 2 limitations.

# SCHEMA
{
  "summary": "2-3 sentence plain-English summary of what the evidence suggests",
  "strongest_signal": "the most compelling single piece of evidence and why",
  "limitations": ["list 2-4 honest limitations"],
  "recommendation": "\"Further investigation recommended\" or \"Evidence is thin — limited conclusions\""
}

# USER
Patent: {title} ({publication_number})
Assignee: {assignees}
Status: {expiry_status} (confidence: {confidence})
Evidence pieces:
{evidence_list_with_tiers}
```

### Narrative anti-patterns (explicitly forbidden in prompt)

- DO NOT use: "is used by," "has been adopted by," "is being commercialized"
- DO NOT name specific products unless they appear in the evidence
- DO NOT estimate market size or revenue
- DO NOT recommend specific business actions ("you should license this")

## 8. Cost Estimate (MVP — 50k patents)

### Assumptions
- 50,000 patents in DB
- MVP evidence sources: forward citations + similar patents only
- Forward citations: assume 30% of patents have any forward citations,
  average 5 per patent → 75,000 citation-based evidence rows
- Similar patents: top-10 similar per patent with embeddings, filtered
  to newer patents → ~3 per patent pass → 150,000 similarity-based
  evidence rows (but heavily filtered by threshold)
- Realistic: ~100,000 evidence rows total, ~15,000 patents with score ≥20

### Compute costs

| Operation | Cost | Notes |
|-----------|------|-------|
| Forward citation ingestion | $0 | Already in DB (if column exists); backfill is a SQL query |
| Semantic similarity | $0 | Uses pgvector `<=>` operator, precomputed embeddings. ~500M comparisons for 50k × 10k recent patents — batch overnight |
| Scoring computation | $0 | Deterministic formula, no LLM |
| LLM narratives | ~$2.50 | 15,000 patents × 2,000 tokens output × Haiku pricing (~$0.000125/1K output tokens) = $3.75. Round to $5 for safety. |

### Storage

| Table | Rows | ~Size |
|-------|------|-------|
| `usage_evidence` | 100,000 | ~50 MB |
| `patent_usage_signals` | 15,000 | ~5 MB |
| AIArtifact rows (narratives) | 15,000 | ~50 MB |
| **Total** | | **~105 MB** |

### LLM calls

- Zero calls for scoring (deterministic)
- ~15,000 calls for narratives if generated for all medium+ patents
- Can batch 5 patents per call → 3,000 total calls, spread over hours
- **Recommendation:** generate narratives asynchronously via backfill,
  not on-demand. Cache as AIArtifacts.

## 9. Out of Scope (Deferred to v2+)

| Item | Why deferred |
|------|-------------|
| Web scraping (product pages, press releases, articles) | Fragile, high-maintenance, legal risk. Needs dedicated infra. |
| Real-time evidence monitoring | Requires event-driven architecture. Batch refresh is sufficient. |
| Jurisdiction-specific evidence | Current data is US-heavy. Non-US patent matching needs INPADOC family data. |
| Product name extraction | Requires NER on evidence text. Significant ML investment. |
| Market size estimation | Hallucination risk. No reliable data source without paid APIs. |
| Competitor analysis reports | Narrative-heavy, multiple LLM calls per report. Cost risk. |
| "Free to use" determinations | Legal liability. Never in scope. |
| GitHub repo matching | Requires code-claim element mapping. Research-grade problem. |
| Standards-essential patent detection | No reliable data source at acceptable cost. |
| Alert triggers for new evidence | Real-time pipeline needed. Defer to Sprint 6 alerts system. |

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Overclaiming** — narrative implies definitive usage when evidence is patent-only | Medium | High — legal + trust damage | Strict prompt guardrails. Every narrative must include "evidence is patent-based only." Human-review gating for score ≥ 70. |
| **False positives** — semantic similarity flags unrelated patents | Medium | Medium | Require ≥1 shared CPC code for strong tier. CPC acts as a hard filter on similarity results. |
| **Stale evidence** — forward citations from 15+ years ago treated as "current" | High | Low | Recency component heavily penalizes old evidence. Evidence >15yr contributes 0 to recency score. |
| **Self-citation inflation** — assignee citing itself boosts score artificially | High | Medium | Self-citations weighted at 1/3. Similar patents from same assignee at 1/2. |
| **Embedding quality** — poor embeddings produce poor similar-patent evidence | Medium | Medium | Minimum similarity threshold of 0.65. Evidence below threshold not stored. |
| **LLM hallucination in narratives** | Medium | High — trust damage | Prompt requires citing specific evidence IDs. Narrative only generated if score ≥ 40. Post-generation validation: does narrative reference real evidence rows? |
| **Storage growth** — evidence rows per patent unbounded | Low | Medium | Cap at 50 evidence rows per patent. Evict weakest on recompute. |
| **User misinterpretation** — user treats signal score as "safety score" | High | High | Every panel must include the mandatory disclaimer. Score label is "usage signal" not "freedom to operate." |
| **Missing data bias** — patents without embeddings or citations get score=0 unfairly | Medium | Low | Score breakdown shows which components contributed. "No data available" empty state with explanation. |
| **Evidence freshness** — evidence grows stale if not recomputed | Medium | Medium | Weekly Celery beat recompute cycle. `most_recent_evidence_date` column on patent_usage_signals tracks age. Evict evidence older than 20 years on each cycle. |
| **Cache invalidation** — narratives stale after recompute | Medium | Low | Don't auto-invalidate on recompute. Mark narrative as "stale — evidence recomputed [date]" if signal row has been updated since generation. User triggers manual regeneration. |
| **pgvector performance at scale** — kNN queries at 50K+ patent corpus | Medium | High | Confirm ivfflat/HNSW index strategy supports sub-second queries BEFORE backfill runs. If not, batch similar-patent collector in the worker; never inline in request path. Measure and report query time before full backfill. |

---

## Decisions (resolved 2026-05-23)

The 5 open questions from the draft scope are now resolved. Rationale
documented for traceability.

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | **Placement:** New tab or panel inside Opportunity? | New "Usage Signals" tab (8th tab, after Legal/Expiry) | Opportunity tab is already long (WhyNow + LinkedIn + narrative). Usage signals are conceptually distinct — mixing them dilutes both. Dedicated tab signals importance. |
| 2 | **Narrative generation trigger:** On-demand or batch? | On-demand with AIArtifact caching (mirrors trend_narrative) | Consistent UX across all AI features. Batch is cheaper but means stale narratives; on-demand with cache gives fast repeated reads and fresh first reads. |
| 3 | **Score threshold for surfacing:** Show "Insufficient" or hide? | Show empty state: "No usage signals detected — evidence below significance threshold. Checked X forward citations and Y similar patents." | Hiding creates impression we didn't check. Empty state with counts educates users about the data that was examined. |
| 4 | **Self-citation policy:** Is 1/3 weighting enough? Warning badge? | 1/3 weighting + warning badge: "⚠ Self-citation risk: N of M evidence pieces share an assignee" when flag is true | Mathematical weighting is subtle; UI badge makes the risk visible. Both layers. |
| 5 | **Expiry Radar integration:** Show no-signal patents or hide? | Show empty state "Usage signals assessed — check patent detail" when no data; real score badge + count when data exists | Consistent with the rest of Expiry Radar: surfaces exist even when empty, with explanation of why. |

---

*End of scope document. Proceeding to implementation plan.*
