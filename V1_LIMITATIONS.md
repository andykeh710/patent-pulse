     1|# Invention Index 8 V1 — Limitations & Demo Notes
     2|
     3|## Deployment Scope
     4|Invention Index 8 V1 is a **single-user local demo application**. It is not intended for public internet deployment without additional hardening.
     5|
     6|## Known Limitations
     7|
     8|### Security
     9|- **No authentication**: Single-user mode only (`local-user`). All routes are publicly accessible.
    10|- **No CSRF protection**: No CSRF tokens on state-changing endpoints.
    11|- **No rate limiting**: API endpoints have no request throttling.
    12|- **No HTTPS**: Runs on plain HTTP (localhost:3000 / localhost:8080).
    13|- **Plaintext secrets**: API keys stored in `.env` file.
    14|
    15|### User Experience
    16|- **Desktop-only**: No responsive/mobile design. Fixed 256px sidebar.
    17|- **No toast notifications**: Mutations (watchlist add/remove, AI generation) have no success/error toasts.
    18|- **No dark mode**: Light theme only.
    19|
    20|### AI Pipeline
    21|- **Sparse AI coverage**: Only 47 of 56,211 patents (0.08%) have opportunity scores. AI enrichment must be run manually via Admin AI Runs.
    22|- **Opportunity narratives**: Often return empty fields when patent lacks claims text. Prompt works best with full patent context.
    23|- **API costs**: Why Now and Opportunity Narrative calls cost ~$0.005/patent via Claude. Use the Admin estimate feature before running batches.
    24|
    25|### Data Quality
    26|- **Assignee normalization incomplete**: The assignee normalization table is empty. Assignee names appear in raw form with duplicates (e.g., "QUALCOMM Incorporated" vs "Qualcomm Incorporated").
    27|- **Legal status confidence**: All patents default to "estimated". Confirmed status requires INPADOC reconciliation (deferred to V1.1).
    28|- **Summarization**: Only patents with abstracts (7,273 of 56,211) can be summarized. The remaining patents need EPO/google-patents enrichment.
    29|
    30|### Deferred to V1.1
    31|| Feature | Reason |
    32||---------|--------|
    33|| Score Re-rank | Only registered as artifact type; no implementation |
    34|| Weekly Digest | No frontend route, no API endpoint |
    35|| Trend Narratives | Trend metrics provide value without narrative |
    36|| Mobile responsive design | Desktop-only for V1 demo |
    37|| Multi-user auth | Single-user mode sufficient for demo |
    38|| INPADOC legal status confirmation | Requires EPO API integration |
    39|
    40|## Running the Demo
    41|
    42|```bash
    43|# Start all services
    44|docker compose up -d
    45|
    46|# Verify health
    47|curl http://localhost:8080/health
    48|
    49|# Open the app
    50|open http://localhost:3000
    51|```
    52|
    53|## Demo Walkthrough
    54|
    55|1. **Dashboard** — Executive snapshot with real counts. Click cards to navigate.
    56|2. **Opportunity** — 47 scored patents across 8 tabs. Use filters to explore.
    57|3. **Trends** — 2,414 trend rows, 415 convergence signals, 407 cliff clusters.
    58|4. **Patents** — 56,211 searchable/filterable patents.
    59|5. **Patent Detail** — Click any patent to see AI summary, tags, scores, and generate Why Now/Opportunity Narrative.
    60|6. **Expiry Watch** — 8,257 patents expiring 2026-2031 with cliff analysis.
    61|7. **Assignees** — 17,420 aggregated assignees ranked by portfolio strength.
    62|8. **Admin AI Runs** — Estimate costs and trigger batch AI operations.
    63|
    64|## Controlling AI Costs
    65|- All LLM calls are cache-first — repeated calls cost $0
    66|- Use `/admin/ai-runs` estimate before running batches
    67|- Auto-approve threshold: $5.00
    68|- Full-batch threshold: $25.00 (requires typing "RUN FULL BATCH")
    69|- Set `LLM_MODE=replay` in `.env` to disable all live API calls
    70|