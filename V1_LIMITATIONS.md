# Patent Pulse V1 — Limitations & Demo Notes

## Deployment Scope
Patent Pulse V1 is a **single-user local demo application**. It is not intended for public internet deployment without additional hardening.

## Known Limitations

### Security
- **No authentication**: Single-user mode only (`local-user`). All routes are publicly accessible.
- **No CSRF protection**: No CSRF tokens on state-changing endpoints.
- **No rate limiting**: API endpoints have no request throttling.
- **No HTTPS**: Runs on plain HTTP (localhost:3000 / localhost:8080).
- **Plaintext secrets**: API keys stored in `.env` file.

### User Experience
- **Desktop-only**: No responsive/mobile design. Fixed 256px sidebar.
- **No toast notifications**: Mutations (watchlist add/remove, AI generation) have no success/error toasts.
- **No dark mode**: Light theme only.

### AI Pipeline
- **Sparse AI coverage**: Only 47 of 56,211 patents (0.08%) have opportunity scores. AI enrichment must be run manually via Admin AI Runs.
- **Opportunity narratives**: Often return empty fields when patent lacks claims text. Prompt works best with full patent context.
- **API costs**: Why Now and Opportunity Narrative calls cost ~$0.005/patent via Claude. Use the Admin estimate feature before running batches.

### Data Quality
- **Assignee normalization incomplete**: The assignee normalization table is empty. Assignee names appear in raw form with duplicates (e.g., "QUALCOMM Incorporated" vs "Qualcomm Incorporated").
- **Legal status confidence**: All patents default to "estimated". Confirmed status requires INPADOC reconciliation (deferred to V1.1).
- **Summarization**: Only patents with abstracts (7,273 of 56,211) can be summarized. The remaining patents need EPO/google-patents enrichment.

### Deferred to V1.1
| Feature | Reason |
|---------|--------|
| Score Re-rank | Only registered as artifact type; no implementation |
| Weekly Digest | No frontend route, no API endpoint |
| Trend Narratives | Trend metrics provide value without narrative |
| Mobile responsive design | Desktop-only for V1 demo |
| Multi-user auth | Single-user mode sufficient for demo |
| INPADOC legal status confirmation | Requires EPO API integration |

## Running the Demo

```bash
# Start all services
docker compose up -d

# Verify health
curl http://localhost:8080/health

# Open the app
open http://localhost:3000
```

## Demo Walkthrough

1. **Dashboard** — Executive snapshot with real counts. Click cards to navigate.
2. **Opportunity** — 47 scored patents across 8 tabs. Use filters to explore.
3. **Trends** — 2,414 trend rows, 415 convergence signals, 407 cliff clusters.
4. **Patents** — 56,211 searchable/filterable patents.
5. **Patent Detail** — Click any patent to see AI summary, tags, scores, and generate Why Now/Opportunity Narrative.
6. **Expiry Watch** — 8,257 patents expiring 2026-2031 with cliff analysis.
7. **Assignees** — 17,420 aggregated assignees ranked by portfolio strength.
8. **Admin AI Runs** — Estimate costs and trigger batch AI operations.

## Controlling AI Costs
- All LLM calls are cache-first — repeated calls cost $0
- Use `/admin/ai-runs` estimate before running batches
- Auto-approve threshold: $5.00
- Full-batch threshold: $25.00 (requires typing "RUN FULL BATCH")
- Set `LLM_MODE=replay` in `.env` to disable all live API calls
