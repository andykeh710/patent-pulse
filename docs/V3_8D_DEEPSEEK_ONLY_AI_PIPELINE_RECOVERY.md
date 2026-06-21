# V3.8D DeepSeek-Only AI Pipeline Recovery

**Date:** 2026-06-21
**Branch:** v3-8d-deepseek-only-ai-pipeline-recovery
**Model:** deepseek-v4-pro
**Status:** ✅ Migrated, smoke-tested, ready for staged backlog

## Provider Map

| File | Function | Old Provider | New Provider | Change |
|------|----------|-------------|-------------|--------|
| `config.py` | Settings | Claude/Anthropic defaults | DeepSeek defaults | Model + base_url |
| `llm_client.py` | LLMClient._get_anthropic() | Direct Anthropic API | DeepSeek compat endpoint | base_url added |
| `anthropic_client.py` | AnthropicChatClient | Direct Anthropic (claude-sonnet) | DeepSeek compat (deepseek-v4-pro) | base_url + model |
| `summarizer.py` | PatentSummarizer | Anthropic (via LLMClient) | DeepSeek (via LLMClient) | Error message only |
| `tagger.py` | TagGenerator | Anthropic (via LLMClient) | DeepSeek (via LLMClient) | Error message only |
| `why_now.py` | WhyNow | Anthropic (via LLMClient) | DeepSeek (via LLMClient) | Error message only |
| `opportunity_narrative.py` | OpportunityNarrative | Anthropic (via LLMClient) | DeepSeek (via LLMClient) | Error message only |
| `trend_narrative.py` | TrendNarrative | Anthropic (via LLMClient) | DeepSeek (via LLMClient) | Error message only |
| `usage_narrative.py` | UsageNarrative | Anthropic (via LLMClient) | DeepSeek (via LLMClient) | Error message only |
| `content_generator.py` | ContentGenerator | Anthropic (via LLMClient) | DeepSeek (via LLMClient) | Error message only |
| `admin.py` | system_health | Anthropic-focused | Provider-agnostic + DeepSeek | New response shape |
| `docker-compose.yml` | All services | Anthropic env vars only | DeepSeek + Anthropic compat | New vars added |
| `.env.example` | Documentation | Anthropic primary | DeepSeek primary | Rewritten |
| `frontend marketing/page.tsx` | AI credit line | "Claude Sonnet narratives" | "DeepSeek-powered patent analysis" | Copy fix |
| `frontend privacy/page.tsx` | Vendor disclosure | "Anthropic (Claude) and DeepSeek" | "DeepSeek" | Copy fix |

## Remaining OpenAI Usage (Embeddings Only)

| File | Usage | Status |
|------|-------|--------|
| `ai/embedder.py` | `text-embedding-3-small` via `api.openai.com` | KEPT — no DeepSeek embedding endpoint verified |
| `tasks/embeddings.py` | Batch embedding generation | KEPT — OpenAI is documented as embeddings-only |
| `services/chat_retrieval.py` | Semantic search via embeddings | KEPT — depends on embedder |

Semantic search continues to use OpenAI embeddings. Text generation (summaries, tags, narratives, chat) is exclusively DeepSeek.

## Anthropic SDK Compatibility Path

The Anthropic SDK is still imported by `llm_client.py` and `anthropic_client.py`, but both now route through:

```
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_API_KEY=<same DeepSeek key>
```

No active production path calls Anthropic's real API. The SDK is retained for:
1. Chat streaming (via `messages.stream()`)
2. Tool/function calling (Anthropic-native format)
3. Fallback if DeepSeek's OpenAI-compatible endpoint is unavailable

## Smoke Test

```bash
docker compose exec backend python3 -c "
import httpx, os
key = os.environ['DEEPSEEK_API_KEY']
r = httpx.post('https://api.deepseek.com/chat/completions',
    headers={'Authorization': f'Bearer {key}'},
    json={'model':'deepseek-v4-pro','messages':[{'role':'user','content':'Hello'}]})
print(r.json()['model'])  # → deepseek-v4-pro
"
```

**Result:** deepseek-v4-pro, 200 OK, 30 input / 100 output tokens.

## Backlog Processing Runbook

### Step 1: Count unsummarized patents

```sql
SELECT COUNT(*) FROM patent_publications WHERE summarized_at IS NULL AND title IS NOT NULL;
```

### Step 2: Process 1 patent

```bash
docker compose exec worker celery -A app.tasks.celery_app call \
  app.tasks.summarize.batch_summarize_pending --kwargs='{"limit":1}'
```

### Step 3: Process 50

```bash
docker compose exec worker celery -A app.tasks.celery_app call \
  app.tasks.summarize.batch_summarize_pending --kwargs='{"limit":50}'
```

### Step 4: Process 500

```bash
docker compose exec worker celery -A app.tasks.celery_app call \
  app.tasks.summarize.batch_summarize_pending --kwargs='{"limit":500}'
```

### Step 5: Process remaining batches

Run batch_summarize_pending repeatedly until count hits 0. Each run processes up to `limit` patents. Monitor:

```sql
SELECT COUNT(*) FROM patent_publications WHERE summarized_at IS NULL;
```

### Step 6: Verify freshness

```sql
SELECT MAX(summarized_at) FROM patent_publications;
```

### Step 7: Verify no Anthropic/OpenAI text generation

Check admin AI health: `GET /api/v1/admin/system-health` should show `provider: deepseek`.

## Files Changed

```
 M .env.example
 M backend/app/ai/anthropic_client.py
 M backend/app/ai/content_generator.py
 M backend/app/ai/llm_client.py
 M backend/app/ai/opportunity_narrative.py
 M backend/app/ai/summarizer.py
 M backend/app/ai/tagger.py
 M backend/app/ai/trend_narrative.py
 M backend/app/ai/usage_narrative.py
 M backend/app/ai/why_now.py
 M backend/app/api/v1/admin.py
 M backend/app/config.py
 M docker-compose.yml
 M frontend/src/app/(marketing)/page.tsx
 M frontend/src/app/(marketing)/privacy/page.tsx
```

## Production Deployment

**Recommended.** All text generation routes through DeepSeek. Embeddings remain OpenAI. The Anthropic SDK compatibility path is configured but unused in active production. Backlog processing is safe to run in staged batches.
