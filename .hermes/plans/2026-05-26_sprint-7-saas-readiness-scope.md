# Sprint 7 — SaaS Readiness (Scope)

**Status:** Decisions locked 2026-05-26.
**Plan-out:** Implementation plan doc to follow.
**Built on:** Sprint 6 (magic-link auth, subscriptions, email).
**Goal per AGENTS.md priority #6:** auth, billing, quotas, exports.

---

## Decisions (locked)

| # | Decision | Choice |
|---|---|---|
| S7-Q1 | Pricing model | **4-tier hybrid: annual subscriptions + one-time lifetime + enterprise** |
| S7-Q2 | Free tier limits | Restrictive: **1 topic, 5 alerts/week, 0 exports** |
| S7-Q3 | Stripe integration | **Stripe Hosted Checkout + Billing Portal** |
| S7-Q4 | Export formats | **CSV + PDF reports** |
| S7-Q5 | Auth | **Magic-link only** (no OAuth) — sufficient per Sprint 6 |

---

## Tier model

| Tier | Price | Billing | Topics | Alerts | CSV export | PDF reports | API access |
|---|---|---|---|---|---|---|---|
| **Free** | $0 | n/a | 1 | 5/week | ❌ | ❌ | ❌ |
| **Basic** | $8 / year | annual recurring | unlimited | unlimited | ✅ | ❌ | ❌ |
| **Lifetime** | $108 once | one-time payment | unlimited | unlimited | ✅ | ✅ | ❌ |
| **Enterprise** | $1000 / year | annual recurring | unlimited | unlimited | ✅ | ✅ | ✅ (API key, rate-limited) |

**Assumptions I'm making — flag any that are wrong before we lock the impl plan:**
1. "Lifetime" = lifetime of the Patent Pulse product (not a fixed N-year period). Customer keeps access until the company shuts down or has a major V2 rebrand.
2. Lifetime users get PDF reports (above Basic tier) but NOT API access (only Enterprise gets API).
3. Enterprise tier includes PDF reports too — superset of Lifetime.
4. Enterprise API = programmatic access to patent search / detail / expiry endpoints via API key auth (separate from the web session cookie). Not a separate "report-generation API" — it's the regular product API exposed for machine consumption.
5. All paid tiers get unlimited topics + alerts (no per-tier alert quotas beyond the Free 5/week cap).
6. Currency = USD only for V1. No multi-currency.
7. Tax = Stripe Tax handles it (auto-collection on Checkout). No manual tax logic.
8. Refunds = handled via Stripe dashboard manually for V1 (no in-app refund flow).

---

## Architecture overview

```
Free user signs up (magic link, Sprint 6) →
  topic_subscriptions table tracks usage →
  quota middleware blocks at limit →
  upgrade CTA → Stripe Hosted Checkout (Basic/Lifetime/Enterprise) →
  Stripe webhook fires →
  backend writes billing_subscription row + flips users.tier →
  user gets paid features unlocked

Enterprise additionally:
  user issues an API key in /account/api-keys →
  request to /api/v1/* with `Authorization: Bearer pp_live_...` header →
  api_key_auth dependency replaces session_cookie auth →
  rate-limited per key + tier
```

---

## Schema (locked)

**New tables (migrations 0016-0019):**

```sql
-- 0016: billing
CREATE TABLE billing_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    tier VARCHAR(16) NOT NULL,  -- 'free' | 'basic' | 'lifetime' | 'enterprise'
    stripe_customer_id VARCHAR(64),
    stripe_subscription_id VARCHAR(64),  -- NULL for lifetime/free
    stripe_payment_intent_id VARCHAR(64),  -- for lifetime one-time
    status VARCHAR(16) NOT NULL,  -- 'active' | 'past_due' | 'canceled' | 'incomplete'
    current_period_end TIMESTAMPTZ,  -- NULL for free/lifetime
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 0017: API keys (Enterprise only)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(128) NOT NULL UNIQUE,  -- SHA-256 of pp_live_...
    key_prefix VARCHAR(16) NOT NULL,  -- e.g. "pp_live_abc123" (first 16 chars for UI display)
    name VARCHAR(128),  -- user-provided label
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 0018: exports (audit + quota tracking)
CREATE TABLE exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    export_type VARCHAR(16) NOT NULL,  -- 'csv' | 'pdf'
    scope VARCHAR(32) NOT NULL,  -- 'expiry_list' | 'trends' | 'patent_report'
    payload_size_bytes INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 0019: extend users with tier helper (denormalized from billing_subscriptions for fast quota checks)
ALTER TABLE users ADD COLUMN tier VARCHAR(16) NOT NULL DEFAULT 'free';
CREATE INDEX ix_users_tier ON users(tier);
```

**Quota enforcement** lives in a FastAPI dependency that reads `users.tier` and applies per-tier limits. The `tier` column is denormalized from `billing_subscriptions.tier` for fast reads — kept in sync via webhook handlers.

---

## Stripe configuration

**Products in Stripe:**
- `prod_basic` — recurring, $8 USD/year
- `prod_lifetime` — one-time, $108 USD
- `prod_enterprise` — recurring, $1000 USD/year

**Webhook events handled:**
- `checkout.session.completed` — both one-time (Lifetime) and recurring (Basic/Enterprise) → write `billing_subscriptions` row, flip `users.tier`
- `invoice.payment_succeeded` — renewal of Basic/Enterprise → update `current_period_end`
- `invoice.payment_failed` — payment failed → set status='past_due'
- `customer.subscription.deleted` — user canceled or failed to renew → set tier='free' after `current_period_end`
- `customer.subscription.updated` — plan change → update tier

**Test mode only until explicit user approval** (per AGENTS.md). Webhook secret + API key both prefixed `sk_test_` / `whsec_test_`.

---

## Implementation chunks (estimated 10 chunks, ~2,200 LOC)

| # | Chunk | LOC | Dependencies |
|---|---|---|---|
| S7-1 | Migrations 0016-0019 + ORM models + tier helper on User | ~150 | S65-4 done |
| S7-2 | Stripe webhook receiver + checkout-session creator endpoint | ~280 | S7-1 |
| S7-3 | Quota middleware (FastAPI dependency, per-tier limits) | ~180 | S7-1 |
| S7-4 | CSV export endpoint (`POST /api/v1/exports/csv`) | ~150 | S7-3 |
| S7-5 | PDF report endpoint (single patent, branded, weasyprint) | ~400 | S7-3 |
| S7-6 | API key issue/revoke/list endpoints + Bearer auth dep | ~200 | S7-1, S7-3 |
| S7-7 | Billing portal frontend (`/account/billing` page) | ~250 | S7-2 |
| S7-8 | Admin dashboard frontend (`/admin` page — user list, tier override) | ~250 | S7-1, S7-7 |
| S7-9 | Tests (Stripe webhook fixtures, quota, exports, API key) | ~300 | all above |
| S7-10 | Live Stripe TEST MODE end-to-end smoke + close-out | n/a | S7-9 |

---

## Operational guardrails (mandatory)

1. **Stripe TEST MODE only.** App refuses to start if `STRIPE_API_KEY` starts with `sk_live_`. Hermes will refuse to use a live key.
2. **Stripe webhook signature verification** required on every webhook handler.
3. **API keys stored hashed** (SHA-256), never plaintext. Shown to the user exactly once at creation time.
4. **Quota middleware fail-closed**: if tier lookup fails, deny the request rather than allow.
5. **PDF reports include the standard AISourceFooter** + "Verify with official registers" caveat.
6. **No "free to use" / "public domain" / "is used by" in any new template or export.**
7. **GDPR alignment**: existing `DELETE /api/v1/account/me` (Sprint 6 L3 deferred) cascade must include `billing_subscriptions`, `api_keys`, `exports`. Sprint 7 must verify the cascade.

---

## Out of scope for Sprint 7 (deferred to V1.1)

- OAuth (Google/GitHub) — magic-link is sufficient
- Multi-currency / international pricing
- In-app refund flow
- Tax invoice / VAT receipts (Stripe Tax handles auto)
- Team accounts / per-seat billing
- Coupon codes / discount codes (Stripe Promotion Codes via dashboard for V1.1)
- Annual-to-lifetime upgrade flow (defer; users buy Lifetime fresh if they want it)
- Usage-based billing (per-alert / per-export) — V1.1 if it makes sense
- API rate limiting (per-key throttle) — basic IP-level rate limit (PR12) is enough for V1
