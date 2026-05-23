# Sprint 4 — Trend Narrative Samples

Generated 2026-05-23 with `tier="summary"` (Sonnet) after Haiku proved
unstable on this schema.

## Sample 1 — cpc/G06F (Computing)

| Field | Value |
|-------|-------|
| Surface | cpc |
| Key | G06F |
| Z-score | 12.8 |
| Growth | +50.9% |
| 4-week patents | 234 |
| 12-week patents | 666 |
| Model | `claude-sonnet-4-20250514` (summary tier, Anthropic API) |

### Patent titles used in payload

1. Tunneling USB2 data using USB4-based configurations — Intel Corporation
2. Pre-silicon power management for next-generation processors — Intel Corporation
3. Unified caching architecture for disaggregated memory — Samsung Electronics

### Narrative JSON

```json
{
  "summary": "Computing System Infrastructure Patents Show Exceptional Filing Activity. Patent filing activity for computing systems and data processing technologies (CPC class G06F) has reached statistically significant levels, with 234 patents filed in the last 4 weeks and 666 in the last 12 weeks. This represents an 18x increase over the historical baseline of 12.8 patents per month, with a z-score of 12.8 indicating this is not normal fluctuation. The activity is led by major semiconductor and technology companies including Intel Corporation and Samsung Electronics...",
  "why_now": "The dramatic increase in G06F patent filings over the last 4-12 weeks, far exceeding historical baselines, suggests a wave of innovation and competitive IP positioning around computing infrastructure technologies including interconnect protocols (USB4), power management, and memory architectures...",
  "key_assignees": ["Intel Corporation", "Samsung Electronics"],
  "related_trends": [
    "USB4/TBT interconnect protocols",
    "Disaggregated computing architectures",
    "Power-optimized processor design"
  ],
  "caveats": [
    "Analysis based solely on patent filing activity, not market validation or commercial success",
    "0% CPC diversity indicates narrow technical focus within G06F classification",
    "Patent abstracts may not reflect full technical scope or commercial intent",
    "Filing surge may reflect strategic patent portfolio building rather than imminent product launches",
    "Four-week snapshot may not represent sustained long-term trend"
  ]
}
```

## Sample 2 — tag/adaptive-treatment-planning (Medical)

| Field | Value |
|-------|-------|
| Surface | tag |
| Key | adaptive-treatment-planning |
| Z-score | varies |
| Growth | varies |
| Model | `claude-sonnet-4-20250514` (summary tier, Anthropic API) |

### Narrative JSON

```json
{
  "summary": "adaptive-treatment-planning patent filing trend analysis.",
  "why_now": "Patent filing activity for adaptive-treatment-planning shows measurable growth over baseline, suggesting increasing R&D interest in personalized and AI-driven treatment planning...",
  "key_assignees": [],
  "related_trends": [],
  "caveats": [
    "Trend analysis is based on patent filing activity and does not constitute market or legal advice."
  ]
}
```

## Sample 3 — assignee/Oomii Inc.

| Field | Value |
|-------|-------|
| Surface | assignee |
| Key | Oomii Inc. |
| Z-score | 0.0 |
| Growth | -100% |
| 4-week patents | 0 |
| Model | `claude-sonnet-4-20250514` (summary tier, Anthropic API) |

### Narrative JSON

```json
{
  "summary": "Patent filing activity for Oomii Inc. shows zero activity in the last 4 weeks, down from prior periods. The decline is pronounced relative to the 12-month baseline, with a negative growth rate.",
  "why_now": "The lack of recent patent filings may indicate a shift in corporate IP strategy, resource reallocation, or a focus on trade secret protection rather than patent prosecution.",
  "key_assignees": [],
  "related_trends": [],
  "caveats": [
    "Zero filing activity in a 4-week window does not necessarily indicate long-term decline",
    "Patent filing activity alone does not reflect overall corporate R&D investment",
    "Trend analysis is based on patent filing activity and does not constitute market or legal advice."
  ]
}
```

## Audit Flag — Haiku reliability

Haiku (`tier="narrative"`) produced unstable JSON envelope structures
during Sprint 4 diagnosis. Three different formats observed in 3 fresh
calls: `{"trend_analysis": {...}}`, `{"trend_summary": "..."}`, and
`{"trend_summary": {"implications": "..."}}`. Switched to Sonnet
(`tier="summary"`) for trend_narrative.

**Affected modules still on Haiku (not yet tested under Sprint 4 conditions):**

| Module | File | Risk |
|--------|------|------|
| `why_now` | `backend/app/ai/why_now.py` | Medium — has explicit SCHEMA instruction; may exhibit empty-envelope behavior on some patents |
| `content_generator` | `backend/app/ai/content_generator.py` | Low — LinkedIn posts are free-form, less schema-dependent |
| `opportunity_narrative` | `backend/app/ai/opportunity_narrative.py` | Medium — structured narrative with SCHEMA constraints |

`trend_snapshot` is deterministic (not LLM-narrative) — no risk.
`assignee_intelligence` and `summarizer` not yet verified for schema stability.

**Recommendation:** Audit all Haiku-tier AI modules post-Sprint 4.
Add `validate_output` envelope handling (like `trend_narrative.py`)
or switch to Sonnet for any module producing structured JSON.

## Model lineage

- Prompt file: `backend/app/ai/prompts/trend_narrative_v1.md`
- Module: `backend/app/ai/trend_narrative.py`
- Tier: `summary` (Sonnet) — switched from `narrative` (Haiku) during Sprint 4
- Reason for switch: Haiku produced 3+ different JSON envelope formats on this schema; Sonnet produces consistent `{title, overview, caveats, ...}` nested under `trend_summary`
