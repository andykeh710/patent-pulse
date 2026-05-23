# Sprint 4 — Trend Intelligence Drilldowns: Implementation Plan

> **Status:** Plan phase. Backend trends API exists. Frontend /trends page has
> 4 tab views. Sprint 4 adds drilldown pages + AI narratives.

## What /trends Currently Does

1. Four tab views: Hot (z-score), Growing (growth %), Convergence (CPC pairs),
   Patent Cliffs (expiry clusters) — all client-rendered from 4 hooks
2. Surface filter (cpc/tag/assignee) for hot/growing tabs; cliff-window filter
   for cliffs tab
3. Summary stat cards: total trends, CPC trends, convergence signals, cliffs
4. URL state: `view`, `surface`, `cliff_window` synced to query params
5. TrendList cards show: surface badge, key label, patent counts, z-score,
   growth % — but cards are **not clickable**

## What Sprint 4 Adds

| Feature | Backend | Frontend |
|---------|---------|----------|
| Trend cards → clickable drilldown | — | Wrap TrendList cards in `<Link>` to `/trends/{surface}/{key}` |
| Patents driving trend | `GET /trends/{surface}/{key}/patents` | Drilldown page section with PatentCard grid |
| Assignees in trend | `GET /trends/{surface}/{key}/assignees` | Bar/list section showing top assignees |
| Time-series chart | Reuse existing TrendSnapshot rows | Simple bar chart or sparkline from multi-week data |
| Linked expiring patents | Filter `/expiry` by CPC/tag from trend | Section with ExpiryRadarCard (reuse from Sprint 2C) |
| Trend narrative | `POST /trends/{surface}/{key}/narrative` | AI-generated, cached as AIArtifact, renders with AISourceFooter |
| "Why matters" summary | Included in narrative output | Shown as lead paragraph above narrative |

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/ai/trend_narrative.py` | AI narrative generator (mirrors why_now.py) |
| `backend/app/ai/prompts/trend_narrative_v1.md` | Prompt file: SYSTEM/SCHEMA/USER |
| `frontend/src/app/trends/[surface]/[key]/page.tsx` | Drilldown page with all sections |

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/api/v1/trends.py` | +3 new endpoints (patents, assignees, narrative) |
| `frontend/src/app/trends/page.tsx` | Wrap trend cards in `<Link>`, make clickable |
| `frontend/src/lib/types.ts` | +TrendDetailResponse, +TrendNarrativeResponse |
| `frontend/src/lib/api.ts` | +trendsApi.getDrilldown() methods |

## Build Order (5 chunks — stop after each)

### Chunk 1 — Backend: 3 new endpoints + tests

Add to `backend/app/api/v1/trends.py`:

1. `GET /trends/{surface}/{key}/patents`
   - Looks up `top_patent_ids` from the latest TrendSnapshot for this
     surface+key, then fetches those PatentPublication rows.
   - Returns `{ items: PatentListItem[], total: int }`
   - Empty/null `top_patent_ids` → empty list, not 404

2. `GET /trends/{surface}/{key}/assignees`
   - Queries patent-publications table for assignees where the patent is
     in this trend's top_patent_ids (via JSONB containment or direct join).
   - Returns `{ items: { assignee: string, count: int }[], total: int }`
   - Empty → empty list

3. `POST /trends/{surface}/{key}/narrative` (and `GET` for cached)
   - POST → calls `generate_trend_narrative()`, returns narrative JSON
   - GET → returns cached artifact if exists, null if not yet generated
   - Cache-first via AIArtifact (same pattern as why_now)
   - Add `TrendNarrativeResponse` schema: `{ summary, why_now, key_assignees,
     related_trends, caveats }`

Add tests in `tests/api/test_trends.py`:
- patents endpoint returns real data for a known surface/key
- patents endpoint returns empty for unknown surface/key
- assignees endpoint returns grouped assignees
- narrative POST returns valid schema
- narrative GET returns cache hit after POST

### Chunk 2 — AI narrative module + prompt

Create `backend/app/ai/trend_narrative.py`:
- Mirror `why_now.py` exactly
- `TREND_NARRATIVE_PROMPT_NAME = "trend_narrative"`
- `build_payload(trend: TrendSnapshot)` — builds prompt variables from
  surface, key, z_score, growth_pct, counts, top_patent_ids
- `validate_output(data)` — enforces { summary, why_now, key_assignees,
  related_trends, caveats }
- `generate_trend_narrative(session, trend)` → `(dict, UUID)`

Create `backend/app/ai/prompts/trend_narrative_v1.md`:
```
# SYSTEM
You are a patent trend analyst. Summarize what is happening in a
technology area based on patent filing activity. Be accurate, cite
data, include caveats. Never invent assignee strategy.

# SCHEMA
{ summary, why_now, key_assignees, related_trends, caveats }

# USER
Surface: {surface}, Key: {key}, Patents (4wk): {count_4w},
Patents (12wk): {count_12w}, Z-score: {z_score},
Growth: {growth_pct}%, Assignee diversity: {diversity}%,
Top patents: {top_patent_ids}
```

### Chunk 3 — Frontend types + API methods

Add to `types.ts`:
- `TrendDrilldownPatentsResponse: { items: PatentListItem[], total: number }`
- `TrendDrilldownAssigneesResponse: { items: { assignee: string, count: number }[], total: number }`
- `TrendNarrativeResponse: { summary: string, why_now: string, key_assignees: string[], related_trends: string[], caveats: string[] }`

Add to `api.ts` (trendsApi):
- `getDrilldownPatents(surface, key)` → `GET /trends/{surface}/{key}/patents`
- `getDrilldownAssignees(surface, key)` → `GET /trends/{surface}/{key}/assignees`
- `generateNarrative(surface, key)` → `POST /trends/{surface}/{key}/narrative`
- `getNarrative(surface, key)` → `GET /trends/{surface}/{key}/narrative`

### Chunk 4 — Frontend: drilldown page

Create `frontend/src/app/trends/[surface]/[key]/page.tsx`:

Sections (top to bottom):
1. **Trend header**: surface badge + key label + z-score + growth %
2. **"Why this matters"** (from narrative if generated, placeholder if not)
3. **Trend narrative** (AI-generated, cached, with generate/regenerate button
   matching WhyNowPanel pattern — useAsyncAction, AISourceFooter)
4. **Patents driving this trend** (paginated list using PatentCard pattern)
5. **Top assignees** (sorted bar list)
6. **Linked expiring patents** (uses expiryApi.list with CPC filter from
   trend key — shows up to 6 ExpiryRadarCards)
7. **Time-series** (simple count-over-time visual from multi-week
   TrendSnapshot data — if available, otherwise empty state)

Reuse: PatentCard, ExpiryRadarCard, AISourceFooter, useAsyncAction,
FreshnessBanner, EmptyState patterns.

URL state: page number for patents section.

Empty states per section explain WHY empty:
- "No patents driving this trend have been identified yet"
- "Narrative not yet generated — click Analyze to create one"
- "No time-series data available for this surface/key"

### Chunk 5 — Make trend cards clickable + verification

Modify `frontend/src/app/trends/page.tsx`:
- Wrap each TrendList card in `<Link href={`/trends/${item.surface}/${item.key}`}>`
- Keep all existing styling, just add clickability and hover state

Full Sprint 4 verification (12 checks):
1. Backend tests (180 + new trend tests)
2. Frontend build clean
3. Frontend tests pass
4. Trend cards are clickable → navigate to drilldown
5. Drilldown page renders for real surface+key
6. Patents section loads real data
7. Assignees section loads real data
8. Narrative generates and caches (second call returns cached)
9. Narrative uses AISourceFooter
10. Linked expiring patents section uses ExpiryRadarCard
11. Empty states explain WHY, not just "no data"
12. No "free to use" / "public domain" language
