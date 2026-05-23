# Patent Pulse — Agent Operating Rules

These rules apply to any AI agent (Hermes, Claude Code, Codex, etc.)
working in this repository. They supplement the generic agent persona
with repo-specific constraints.

## Development Priorities

When choosing what to build or improve, prioritize in this order:

1. **Expiry accuracy and coverage** — confidence labels, maintenance-fee
   awareness, active-family-risk visibility, expiry-opportunity scoring.
2. **Patent understanding** — claims display, family viewer, citations,
   assignee profiles, external patent-office links, similar patents.
3. **Filing trends and assignee movement** — drilldowns, explanations,
   trend-to-expiry linkage, trend narratives.
4. **Commercial usage signals** — evidence-backed discovery of where
   expired/expiring patent ideas appear in current products, companies,
   markets, or newer patents. **Never overclaim.**
5. **User topics, alerts, newsletters** — subscription-based intelligence
   delivery.
6. **SaaS readiness** — auth, billing, quotas, exports.
7. **Content generation** — LinkedIn posts, reports, newsletters as
   downstream packaging only. Do not treat as a core feature.

## Patent Data Rules

- **Real data only.** Every patent record must originate from a real
  patent office feed (USPTO, EPO, etc.). Never create synthetic patent
  records for testing without the `dev_fixture` marker.
- **No invented market data.** Do not generate market sizes, revenue
  figures, competitor names, or product launch dates unless explicitly
  present in the source data.
- **No invented assignee strategy.** Do not speculate about what a
  company is planning based on patent filings alone.

## Patent Figures and Images

- **Link-only, never host.** Patent figures must be embedded via remote
  `<img src>` pointing to the originating patent office (USPTO, Google
  Patents, Espacenet). Do not download, cache, or re-serve figure
  images without prior licensing review.
- **Attribute the source.** Display "Image © patent office — verify at
  source" on hover or below the figure.
- **Graceful degradation.** When a figure URL is null or returns an
  error, show no broken image — render the empty state cleanly.

## Expiry and Legal Claims

- **Never label a patent "free to use" or "public domain."** Expiry
  status is always estimated unless confirmed. Always show confidence
  levels.
- **Always surface active family risk.** A patent may be expired in one
  jurisdiction but have active family members elsewhere.
- **Always include "verify with official registers" caveats** on
  expiry-related surfaces.
- **Distinguish estimated from confirmed expiry.** Use explicit labels:
  `active_estimated`, `expiring_soon`, `expired_estimated`,
  `lapsed_possible`, `lapsed_confirmed`, `expired_confirmed`, `unknown`.

## Commercial Usage Claims

- **Never say "this patent is used in Product X"** unless there is
  definitive evidence (e.g., a court finding, the product's own patent
  markings, or an official standard document).
- **Prefer evidence-backed language:**
  - "appears related to"
  - "shows technical overlap with"
  - "suggests market relevance"
  - "may indicate commercial usage"
- **Always show evidence tier** (strong / medium / weak) and source links.
- **Always include limitations** with any usage signal narrative.

## AI-Generated Content

- All LLM output must be cached as `AIArtifact` rows.
- All AI-generated content displayed to users must include
  `AISourceFooter` or equivalent labeling.
- Confidence levels must be shown where applicable.
- Source citations and evidence IDs must be included where available.

## Implementation Conventions

- **Follow the existing pattern.** New AI modules mirror the structure
  of existing ones (e.g., `why_now.py`, `summarizer.py`). Use the same
  `LLMRequest`/`LLMClient`/`AIArtifact` caching stack.
- **Prompt files are the source of truth.** Prompts live in
  `backend/app/ai/prompts/<name>_v<version>.md`. Any edit changes the
  hash and forces regeneration.
- **Migrations are explicit.** Every schema change gets an Alembic
  migration. Never use `create_all()` in production code.
- **Tests for every endpoint.** API tests use `AsyncMock` on the
  generator function at the endpoint level (not the underlying AI
  module). Database tests use the real test DB.
- **Frontend panels follow the pattern.** New intelligence panels
  mirror `WhyNowPanel` / `OpportunityNarrativePanel` structure:
  loading, empty, success, error states.
- **Evidence before LLM.** When implementing expiry or usage features,
  prefer deterministic assessments and evidence tables before LLM
  narratives. LLMs may summarize evidence, but they must not create
  the evidence. Evidence comes from patent records, family records,
  citation records, and official links — not from model imagination.

## Plan Deviations

If an implementation plan specifies one contract and you find yourself
implementing something different — different field names, different
schema shape, different API response — stop and report the deviation
before applying it. Silent deviations become bugs.

## File Conventions

- **Plans** live in `.hermes/plans/` — one file per feature phase.
- **Product strategy** lives in `PRODUCT_STRATEGY.md`.
- **Roadmap** lives in `ROADMAP.md`.
- **Agent rules** live in this file (`AGENTS.md`).
- **Hermes memory** is for volatile project state and user preferences,
  not static identity or rules.
