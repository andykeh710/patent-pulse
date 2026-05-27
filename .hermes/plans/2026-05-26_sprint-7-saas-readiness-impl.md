# Sprint 7 — SaaS Readiness (Implementation Plan)

**Scope:** [.hermes/plans/2026-05-26_sprint-7-saas-readiness-scope.md](.hermes/plans/2026-05-26_sprint-7-saas-readiness-scope.md)
**Decisions locked:** 2026-05-26.
**Model:** 4-tier hybrid (Free/Basic $8yr/Lifetime $108/Enterprise $1000yr).
**Billing:** Stripe Hosted Checkout + Billing Portal (TEST MODE only).
**Auth:** Magic-link only (Sprint 6). Session cookie + Bearer API key.

---

## Build Order (10 chunks)

### S7-1 — Migrations 0016-0019 + ORM models + tier helper

**Files:**
- Create: `backend/alembic/versions/0016_add_billing_subscriptions.py`
- Create: `backend/alembic/versions/0017_add_api_keys.py`
- Create: `backend/alembic/versions/0018_add_exports.py`
- Create: `backend/alembic/versions/0019_add_users_tier.py`
- Create: `backend/app/core/billing_models.py` (BillingSubscription, APIKey, Export)
- Modify: `backend/app/core/ai_models.py` — add `tier` column to User

**Acceptance:**
- `alembic upgrade head` advances 0015 → 0019 cleanly
- `alembic downgrade -1` works back to 0018, then all the way to 0015
- ORM models importable, register with Base.metadata
- `users.tier` column exists with default `'free'` and index

**DEVIATION DETECTED triggers:**
- If column name conflicts (e.g. `User.tier` already exists) → STOP
- If migration order conflicts with existing migrations → STOP

---

### S7-2 — Stripe webhook receiver + checkout-session creator

**Files:** backend/app/billing/__init__.py, stripe_client.py, api/v1/billing.py, router.py

**Endpoints:** POST /checkout-session, POST /webhook

**Stripe guard:** refuses to start if STRIPE_API_KEY starts with `sk_live_`

---

### S7-3 through S7-10

See scope doc §"Implementation chunks" for full outline. Each chunk:
- Quota middleware (S7-3)
- CSV export (S7-4)
- PDF report (S7-5)
- API key management (S7-6)
- Billing portal frontend (S7-7)
- Admin dashboard (S7-8)
- Tests (S7-9)
- Live smoke (S7-10)

---

## Operating Rules (carried forward)

- LITERAL pytest -q tail in every verification block
- DEVIATION DETECTED = stop, present A/B/C, WAIT
- No --ignore, no skip-as-pass, no xfail-as-pass, no `as any`
- Stripe TEST MODE only; refuse `sk_live_` keys
- Session-injection pattern for async tasks (S6-9 lesson)
- Stop after every chunk; user commits; user replies with next chunk ID
