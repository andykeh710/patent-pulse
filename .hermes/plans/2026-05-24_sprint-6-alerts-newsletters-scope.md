# Sprint 6 — User Alerts & Newsletters (Scope)

**Status:** Decisions locked 2026-05-24. Ready for implementation plan-out.

**Built on:** Phase 3 (user-created topics, already shipped). The `themes`
table already has `user_id`, `keywords`, `opportunity_tags`,
`min_opportunity_score`. The `users` table has `id`, `email`, `preferences (jsonb)`.

**Goal per AGENTS.md priority #5:** subscription-based intelligence delivery —
let users subscribe to topics and receive periodic digests / alerts.

---

## Decisions (locked)

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | Design approach | **Hybrid (C)** — per-subscription mode enum: `instant_alert` or `weekly_digest` | Matches the dual use case of "tell me NOW about X" vs "summarize my week." Modest LLM cost (weekly only). |
| 2 | Email provider | **Resend** | Modern API, 3K/month free tier, simple Python SDK, good deliverability. |
| 3 | Auth | **Magic-link** (build now) | ~200 LOC, no passwords. Reused in Sprint 7. Enables real user identification for Sprint 6 delivery. |
| 4 | Subscription shape | **Dedicated `topic_subscriptions` table** | Indexable, aggregatable, clean migration path. |
| 5 | Channel | Email-only for Sprint 6. In-app feed deferred. | Reduces scope; email covers both alert types. |
| 6 | Weekly briefing model | **Sonnet** (`tier="summary"`) | Per Sprint 4/Audit-A3 lesson — Haiku envelope unreliability. Sonnet for structured narratives. |
| 7 | Operational guardrails | **No broad sends without explicit approval** | First batch goes to dev users only. Production sends require user sign-off. |

---

## Architecture overview

```
┌──────────────┐   subscribes   ┌─────────────────────┐
│    User      │ ─────────────► │ topic_subscriptions │
│ (magic link) │                │  (user_id, theme_id,│
└──────────────┘                │   mode, frequency)  │
                                └────────┬────────────┘
                                         │
              ┌──────────────────────────┼─────────────────────────┐
              ▼                                                    ▼
   ┌─────────────────────┐                          ┌─────────────────────────┐
   │  Instant Alert path │                          │   Weekly Digest path    │
   │ Theme matcher post- │                          │  Sunday 7am beat job    │
   │  hook ────► email   │                          │   ► gather matches      │
   │ (filter-only HTML)  │                          │   ► Sonnet briefing     │
   └──────────┬──────────┘                          │   ► cache as AIArtifact │
              │                                     │   ► email (rich HTML)   │
              ▼                                     └─────────┬───────────────┘
        ┌──────────────────────────────────────────────────────┘
        ▼
┌────────────────────┐
│  Resend SDK send   │  → tracks delivery state per-message
└────────────────────┘
```

---

## Schema (locked)

**New table: `topic_subscriptions`** (migration 0012)

```sql
CREATE TABLE topic_subscriptions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    theme_id      UUID NOT NULL REFERENCES themes(id) ON DELETE CASCADE,
    mode          VARCHAR(16) NOT NULL,  -- 'instant_alert' | 'weekly_digest'
    min_score     FLOAT,                 -- optional: only fire on opportunity_score >= this
    last_delivered_at  TIMESTAMP,
    paused        BOOLEAN NOT NULL DEFAULT false,
    created_at    TIMESTAMP NOT NULL DEFAULT now(),
    updated_at    TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE(user_id, theme_id, mode)
);
CREATE INDEX ix_topic_subscriptions_user ON topic_subscriptions(user_id);
CREATE INDEX ix_topic_subscriptions_theme ON topic_subscriptions(theme_id);
```

**Reuses existing `users.email`** for delivery; no schema changes there.

**New table: `auth_magic_link_tokens`** (migration 0013, for magic-link auth)

```sql
CREATE TABLE auth_magic_link_tokens (
    token_hash    VARCHAR(128) PRIMARY KEY,  -- SHA-256 of the actual token
    user_id       VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email         VARCHAR(256) NOT NULL,
    expires_at    TIMESTAMP NOT NULL,
    consumed_at   TIMESTAMP,
    created_at    TIMESTAMP NOT NULL DEFAULT now()
);
```

**New table: `email_deliveries`** (migration 0014, deliverability tracking)

```sql
CREATE TABLE email_deliveries (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           VARCHAR(64) NOT NULL REFERENCES users(id),
    subscription_id   UUID REFERENCES topic_subscriptions(id) ON DELETE SET NULL,
    email_type        VARCHAR(32) NOT NULL,  -- 'magic_link' | 'instant_alert' | 'weekly_digest'
    resend_message_id VARCHAR(64),
    status            VARCHAR(16) NOT NULL,  -- 'sent' | 'delivered' | 'bounced' | 'failed'
    sent_at           TIMESTAMP NOT NULL DEFAULT now(),
    artifact_id       UUID REFERENCES ai_artifacts(id)  -- for weekly digest narratives
);
CREATE INDEX ix_email_deliveries_user ON email_deliveries(user_id, sent_at);
```

---

## Implementation plan outline (9 chunks)

| # | Chunk | Files | LOC est. |
|---|---|---|---|
| 1 | Migrations 0012-0014 + ORM models | `0012-0014.py`, `core/models.py`, `core/auth_models.py` | ~120 |
| 2 | Magic-link auth backend | `auth/magic_link.py`, `api/v1/auth.py`, `api/deps.py` (current_user dep) | ~250 |
| 3 | Magic-link auth frontend | `app/login/page.tsx`, `app/login/verify/page.tsx`, AuthContext | ~150 |
| 4 | Subscription API | `api/v1/subscriptions.py` (list/create/update/delete) | ~180 |
| 5 | Resend email module | `email/sender.py` (thin SDK wrapper), templates dir | ~100 |
| 6 | Instant alert hook | extend `theme_matcher.py` post-hook → enqueue email task | ~80 |
| 7 | Weekly digest Sonnet briefing | `ai/weekly_digest.py` + `prompts/weekly_digest_v1.md`, beat schedule | ~200 |
| 8 | Frontend subscription UI | `app/topics/[id]/page.tsx` subscribe panel, `app/account/page.tsx` | ~180 |
| 9 | Tests + language audit + dev-only-send guard | `tests/auth/`, `tests/email/`, `tests/subscriptions/` | ~250 |

**Total estimate: ~1,500 LOC across backend + frontend.**

---

## Operational guardrails (mandatory)

1. **Production-send guard.** A `EMAIL_SEND_MODE` env var with three values:
   - `dev` (default): emails go to a single dev recipient via Resend `to:`
     override; subject prefixed `[DEV →` + real recipient.
   - `dry_run`: log to DB only, no Resend call.
   - `production`: send for real. **Requires explicit user approval to set.**
2. **Unsubscribe link in every email** (legal compliance — CAN-SPAM / GDPR).
3. **All Sonnet weekly briefings cached as AIArtifact** + must include
   `AISourceFooter` equivalent ("AI-generated weekly summary — verify
   patent claims at source").
4. **No "free to use" / "public domain" language** in any template.
   Language audit mandatory before declaring done (per AGENTS.md).
5. **Rate limit Resend calls.** Max 100/hour to start, configurable.
   Bouncing emails > 3× → auto-pause subscription.
6. **Magic-link expiry** = 15 minutes. Token use is single-shot
   (consumed_at set).

---

## Cost estimate

- **Resend free tier**: 3,000/month emails, 100/day. Fits dev + early-stage.
- **Sonnet weekly briefings**: ~1K input tokens + 600 output ≈ $0.012 per
  briefing. At 100 subscribers × 4 weeks = $4.80/month. Negligible.
- **Magic links**: ~50 tokens per email, negligible.

---

## Out of scope for Sprint 6 (deferred)

| Item | Deferred to |
|---|---|
| Stripe billing / paid tier | Sprint 7 |
| Quotas / rate-limits per user | Sprint 7 |
| Mobile push notifications | post-V1 |
| SMS alerts | post-V1 |
| Webhook delivery | post-V1 |
| In-app feed page | Sprint 6.5 if requested |
| OAuth (Google/GitHub) | Sprint 7 |
| Audit log of email opens / clicks | post-V1 |
