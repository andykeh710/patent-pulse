# S2 Score Manifest

Inventory of every heuristic score render, produced before replacement.

## Replaced (heuristic scores → `<Score>`)

| File | Line(s) | Score Field | Legacy Render | Target |
|------|---------|------------|---------------|--------|
| `patents/PatentCard.tsx` | 49-50 | opportunity_score, interesting_score | `<OpportunityScoreBadge>` + `<ScoreBadge>` | `<Score kind="opportunity">` + `<Score kind="interesting">` |
| `patents/[id]/page.tsx` | 437-438 | opportunity_score, interesting_score | `<OpportunityScoreBadge>` + `<ScoreBadge>` | `<Score kind="opportunity">` + `<Score kind="interesting">` |
| `opportunity/page.tsx` | 298-299 | opportunity_score, interesting_score | `<OpportunityScoreBadge>` + `<ScoreBadge>` | `<Score kind="opportunity">` + `<Score kind="interesting">` |
| `today/page.tsx` | 519 | opportunity_score | `<OpportunityScoreBadge>` | `<Score kind="opportunity">` |
| `today/page.tsx` | 163, 166 | opportunity_score | `toFixed(1)` in string | `<Score>` where html, `Math.round()` where string |
| `today/page.tsx` | 563-570 | supplier_score | inline color-coded span | `<Score kind="composite">` |
| `today/page.tsx` | 623, 630 | opportunity_score | `toFixed(1)` in string | `Math.round()` (string context) |
| `watchlist/page.tsx` | 126-129 | opportunity_score | `toFixed(0)` in Badge | `<Score kind="opportunity">` |
| `companies/page.tsx` | 322 | supplier_score | inline color-coded span | `<Score kind="composite">` |
| `companies/[name]/page.tsx` | 109 | supplier_score | inline color-coded span | `<Score kind="composite">` |
| `companies/[name]/page.tsx` | 156-158 | opportunity_score | inline `Math.round()` | `<Score kind="opportunity">` |
| `companies/[name]/page.tsx` | 204-207 | signal_score | inline `toFixed(1)` | `<Score kind="composite">` (avg signal score) |
| `patents/page.tsx` | 112-113 | interesting_score, opportunity_score | sort options only (dropdown values) | N/A — sort field names stay |
| `c/[name]/page.tsx` | 147 | signal_score | inline `String(Math.round())` | `<Score kind="composite">` (but value is string type) |

## Retired components

- `patents/ScoreBadge.tsx` — replaced by `<Score kind="interesting">`
- `patents/ScoreBadge.test.tsx` — delete with component
- `patents/OpportunityScoreBadge.tsx` — replaced by `<Score kind="opportunity">`

## Orphaned utils to remove

- `lib/utils.ts`: `getScoreLabel`, `getScoreBgClass`, `getScoreColor`, `getOpportunityLabel`, `getOpportunityBgClass`
  (Only used by ScoreBadge / OpportunityScoreBadge)

## Intentionally Preserved (statistical / non-heuristic)

| Field | Reason | Files |
|-------|--------|-------|
| `z_score.toFixed(1)` | Statistical z-score, not heuristic | today/page.tsx, trends/page.tsx, trends/[surface]/[key]/page.tsx |
| `growth_pct.toFixed(1)` | Growth percentage | trends/page.tsx, trends/[surface]/[key]/page.tsx |
| `growth_ratio.toFixed(1)` | Growth ratio | trends/page.tsx |
| `assignee_diversity` | Diversity percentage | trends/page.tsx |
| `cpc_diversity` | Diversity percentage | trends/[surface]/[key]/page.tsx |
| `daysUntilExpiry` / year calcs | Time calculations | ExpiryRadarCard.tsx |
| `est_cost_usd.toFixed(4)` | Administrative cost | admin/ai-runs/page.tsx |
| `payload_size_bytes` / KB | Administrative metric | admin/page.tsx |
| `baseline_12mo.toFixed()` | Statistical baseline | trends/[surface]/[key]/page.tsx |
