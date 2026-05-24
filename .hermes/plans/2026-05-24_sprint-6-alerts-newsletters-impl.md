# Sprint 6 — User Alerts & Newsletters (Implementation Plan)

**Scope reference:** [.hermes/plans/2026-05-24_sprint-6-alerts-newsletters-scope.md](.hermes/plans/2026-05-24_sprint-6-alerts-newsletters-scope.md) — decisions locked 2026-05-24.

**Model:** Sonnet (`tier="summary"`) for weekly briefings. No Haiku (per A3 audit).
**Email:** Resend (Python SDK).
**Auth:** Magic-link (built here, reused in Sprint 7).
**Send guard:** `EMAIL_SEND_MODE` env var — defaults to `dev` (override recipient to a single dev address). Must be flipped to `production` by user before broad sends.

---

## Build Order (9 chunks)

### 1. Migrations + ORM models

**Files (create):**
- `backend/alembic/versions/0012_add_topic_subscriptions.py`
- `backend/alembic/versions/0013_add_auth_magic_link_tokens.py`
- `backend/alembic/versions/0014_add_email_deliveries.py`
- `backend/app/core/subscription_models.py` (new ORM module)

**Schema** (per scope doc — repeat here for completeness):

```sql
-- 0012
CREATE TABLE topic_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    theme_id UUID NOT NULL REFERENCES themes(id) ON DELETE CASCADE,
    mode VARCHAR(16) NOT NULL,            -- 'instant_alert' | 'weekly_digest'
    min_score FLOAT,
    last_delivered_at TIMESTAMP,
    paused BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (user_id, theme_id, mode)
);

-- 0013
CREATE TABLE auth_magic_link_tokens (
    token_hash VARCHAR(128) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(256) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    consumed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

-- 0014
CREATE TABLE email_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(id),
    subscription_id UUID REFERENCES topic_subscriptions(id) ON DELETE SET NULL,
    email_type VARCHAR(32) NOT NULL,
    resend_message_id VARCHAR(64),
    status VARCHAR(16) NOT NULL,
    sent_at TIMESTAMP NOT NULL DEFAULT now(),
    artifact_id UUID REFERENCES ai_artifacts(id)
);
```

**Acceptance:**
- `alembic upgrade head` advances 0011 → 0014 cleanly.
- `\d topic_subscriptions` and the two other tables exist with correct
  FKs and indexes.
- ORM models import cleanly + register with `Base.metadata`.

---

### 2. Magic-link auth backend

**Files:**
- Create: `backend/app/auth/__init__.py`
- Create: `backend/app/auth/magic_link.py` — token issue + verify functions
- Create: `backend/app/api/v1/auth.py` — `/auth/request-link`, `/auth/verify`, `/auth/me`, `/auth/logout`
- Modify: `backend/app/api/deps.py` — add `current_user()` dependency
- Modify: `backend/app/api/v1/router.py` — include auth router
- Modify: `backend/app/config.py` — add `auth_secret_key`, `magic_link_ttl_minutes` (default 15), `magic_link_base_url`

**Endpoints:**
- `POST /api/v1/auth/request-link {email}` → 202; emails a one-shot
  link `/auth/verify?token=...`. Always 202 (don't disclose whether
  the email exists).
- `GET /api/v1/auth/verify?token=...` → 302 redirect to frontend with
  a session cookie set (HttpOnly, SameSite=Lax, Secure in prod).
  Consumes the token (sets `consumed_at`). Rejects if expired or
  already consumed.
- `GET /api/v1/auth/me` → current user info from cookie session.
- `POST /api/v1/auth/logout` → clear session cookie.

**Token strategy:**
- Generate 32-byte URL-safe random token.
- Store ONLY `SHA-256(token)` server-side (constant-time hash, salt via
  `auth_secret_key`).
- Email contains the raw token; verify by hashing again.
- TTL: 15 min, single-use.

**Session strategy:**
- Sign a JWT (HS256, `auth_secret_key`) with `sub=user_id`, `exp=now+30d`.
- Set as `auth_session` HttpOnly cookie.
- `current_user()` dependency reads cookie, verifies JWT, looks up user.

**Acceptance:**
- Request-link with unknown email → 202 (no enumeration disclosure).
- Request-link with known email → creates token row + (in dev mode)
  prints magic link to log.
- Verify with valid token → 302 + cookie. Subsequent `/auth/me` returns
  user.
- Verify with consumed token → 400.
- Verify with expired token → 400.
- Unit tests cover all 4 paths.

---

### 3. Magic-link auth frontend

**Files:**
- Create: `frontend/src/app/login/page.tsx` — email input form
- Create: `frontend/src/app/login/check/page.tsx` — "check your email" landing
- Create: `frontend/src/app/login/verify/page.tsx` — reads `?token=...` from URL, calls API, redirects to /
- Create: `frontend/src/lib/auth/AuthContext.tsx` — useAuth() hook with current_user state
- Modify: `frontend/src/app/layout.tsx` — wrap with AuthProvider
- Modify: `frontend/src/lib/api.ts` — `authApi.requestLink`, `authApi.verify`, `authApi.me`, `authApi.logout`

**Acceptance:**
- `/login` form posts email → success state ("Check your email").
- `/login/verify?token=...` shows spinner, calls API, redirects to / on
  success, shows error on failure.
- `useAuth()` returns `{user, isLoading, isAuthenticated, logout}`.
- Protected routes (subscriptions, account) redirect to /login if not
  authenticated.

---

### 4. Subscription API

**Files:**
- Create: `backend/app/api/v1/subscriptions.py`
- Modify: `backend/app/api/v1/router.py` — include subscriptions router
  under `/subscriptions`

**Endpoints (all require `current_user` dependency):**

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/subscriptions` | List current user's subscriptions |
| `POST` | `/api/v1/subscriptions` | Create subscription `{theme_id, mode, min_score?}` |
| `PATCH` | `/api/v1/subscriptions/{id}` | Update mode / min_score / paused |
| `DELETE` | `/api/v1/subscriptions/{id}` | Unsubscribe |
| `GET` | `/api/v1/subscriptions/unsubscribe?token=...` | Public 1-click unsubscribe (signed token, no login) |

**Unsubscribe token:** HMAC of subscription_id signed with
`auth_secret_key`. Embedded in every email's footer. Clicking flips
`paused=true` and redirects to a "you're unsubscribed" page.

**Acceptance:**
- All authenticated endpoints reject without cookie → 401.
- User can only see/modify their own subscriptions (ownership enforced).
- Unique constraint enforced: duplicate (user, theme, mode) → 409.
- Unsubscribe link works without authentication.

---

### 5. Resend email module

**Files:**
- Create: `backend/app/email/__init__.py`
- Create: `backend/app/email/sender.py` — thin Resend SDK wrapper with
  send-mode guard
- Create: `backend/app/email/templates/__init__.py`
- Create: `backend/app/email/templates/magic_link.html`
- Create: `backend/app/email/templates/instant_alert.html`
- Create: `backend/app/email/templates/weekly_digest.html`
- Modify: `backend/app/config.py` — add `resend_api_key`,
  `email_send_mode` (default `dev`), `email_dev_recipient`,
  `email_from_address` (default `alerts@patent-pulse.dev`)

**`sender.send_email()` contract:**
```python
async def send_email(
    *,
    user_id: str,
    to_email: str,
    subject: str,
    html_body: str,
    email_type: str,
    subscription_id: UUID | None = None,
    artifact_id: UUID | None = None,
) -> str | None:
    """Returns resend_message_id on success, None on dry-run.
    Writes email_deliveries row regardless of mode."""
```

**Send-mode behavior:**
- `dev` (default): rewrite `to_email` → `settings.email_dev_recipient`;
  prefix subject `[DEV → {original_email}]`. Still calls Resend.
- `dry_run`: write `email_deliveries` row with `status='dry_run'`,
  skip Resend call.
- `production`: send for real. **Production mode requires an explicit
  startup-check that the user has set the env var.** Log warning if
  switched to production for first time.

**Templates:** Jinja2 + simple HTML. Mandatory footer in all templates:
```
This email was sent because you subscribed to {theme_name} on Patent Pulse.
[Unsubscribe with one click]({unsubscribe_url})
Patent Pulse · Evidence-backed signals · Verify with official registers.
```

**Acceptance:**
- Send in dev mode → Resend message ID returned, recipient rewritten,
  delivery row written.
- Send in dry_run mode → no Resend call, delivery row written with
  status='dry_run'.
- Send in production mode → real send, delivery row written.
- Resend bounce webhook (optional Sprint 6.5) → mark delivery `bounced`.

---

### 6. Instant alert hook

**Files:**
- Modify: `backend/app/tasks/theme_matcher.py` — after writing a new
  `theme_matches` row, enqueue alert send for any matching subscriptions
- Create: `backend/app/tasks/send_instant_alert.py` — Celery task that
  renders + sends a single alert email
- Modify: `backend/app/tasks/celery_app.py` — register the new task

**Flow:**
```
new theme_match row written
   ↓
query topic_subscriptions WHERE theme_id = match.theme_id
                            AND mode = 'instant_alert'
                            AND NOT paused
   ↓ for each matching subscription
enqueue send_instant_alert(subscription_id, patent_id, match_id)
   ↓ task runs
render template + call sender.send_email
update last_delivered_at on subscription
```

**Acceptance:**
- Theme matcher writing a new match for a subscribed theme fires the
  task within 60s.
- Email contains: patent title, assignee, link to patent detail, brief
  why-it-matters (use existing `summary` if present, else first 200
  chars of abstract), unsubscribe footer.
- Two subscriptions to same theme → two emails (independent).
- `min_score` filter respected (subscription with `min_score=70` doesn't
  fire for patent with score=50).

---

### 7. Weekly digest Sonnet briefing

**Files:**
- Create: `backend/app/ai/weekly_digest.py` (mirrors `usage_narrative.py`
  pattern — `build_payload`, `validate_output`, `generate_weekly_digest`)
- Create: `backend/app/ai/prompts/weekly_digest_v1.md`
- Create: `backend/app/tasks/send_weekly_digest.py` — Celery beat task
- Modify: `backend/app/tasks/celery_app.py` — register + beat schedule
  (Sunday 7am: per-user fan-out)

**Prompt schema:**
```json
{
  "headline": "string — 1-sentence summary of the week",
  "highlights": [
    {"patent_doc_id": "USPTO:...", "title": "...", "why_it_matters": "..."}
  ],
  "patterns": "string — 2-3 sentences on cross-topic patterns observed",
  "caveats": ["string — evidence limitations"]
}
```

**Forbidden phrases (per AGENTS.md):** "free to use", "public domain",
"is used by", "definitely used".

**Cache:** Per-user briefing cached as `AIArtifact` (artifact_type =
`weekly_digest`). Prompt hash + input hash include user_id + week
boundary, so each user-week is independent.

**Beat schedule:**
```python
"weekly-digest-sunday": {
    "task": "app.tasks.send_weekly_digest.fan_out_weekly_digests",
    "schedule": crontab(hour=7, minute=0, day_of_week=0),
    "options": {"queue": "summarization"},
}
```

**Fan-out logic:** task fetches all (user, subscriptions) with
`mode='weekly_digest'`, groups by user, generates one briefing per user
across their topics, sends.

**Acceptance:**
- Sunday 7am fires fan-out task.
- Each user with active digest subscriptions receives one email.
- Sonnet output passes `validate_output` (forbidden-phrase rejection +
  schema enforcement).
- Cache hit on re-fan-out within same week returns same content.
- Output cached as AIArtifact with proper type label.

---

### 8. Frontend subscription UI

**Files:**
- Modify: `frontend/src/app/themes/[id]/page.tsx` (or wherever topic
  detail lives) — add "Subscribe" panel with mode toggle + min-score
  slider
- Create: `frontend/src/app/account/page.tsx` — list current
  subscriptions, allow pause/unpause/delete
- Modify: `frontend/src/lib/api.ts` — `subscriptionsApi.list/create/update/delete`
- Modify: `frontend/src/lib/types.ts` — add `TopicSubscription`, `SubscriptionMode`
- Modify: `frontend/src/app/NavSidebar.tsx` — add Account link when
  authenticated

**Subscribe panel UI:**
```
┌────────────────────────────────────────┐
│  Subscribe to "Semiconductor Memory"    │
│                                         │
│  ○ Instant alerts (email on match)      │
│  ● Weekly digest (Sunday morning)       │
│                                         │
│  Min opportunity score: [slider 0-100]  │
│                                         │
│  [ Subscribe ]                          │
└────────────────────────────────────────┘
```

**Acceptance:**
- Authenticated user can subscribe from topic detail page.
- Subscribe panel respects existing subscription (shows pause/edit
  instead of subscribe button).
- Account page lists all subscriptions with delivery info.
- Unsubscribe link from email lands on a friendly "You're unsubscribed"
  page.

---

### 9. Tests + language audit + send-mode guard

**Files (create):**
- `backend/tests/auth/test_magic_link.py` — issue + verify + expire +
  consume
- `backend/tests/auth/test_session.py` — JWT verification, current_user
  dependency
- `backend/tests/api/test_subscriptions.py` — CRUD + ownership + 401
- `backend/tests/email/test_sender.py` — dev/dry_run/production modes
- `backend/tests/email/test_templates.py` — Jinja render, unsubscribe
  link present
- `backend/tests/tasks/test_send_instant_alert.py` — hook + delivery
- `backend/tests/tasks/test_send_weekly_digest.py` — fan-out + Sonnet
  cache hit
- `backend/tests/ai/test_weekly_digest.py` — `validate_output` +
  forbidden phrases

**Language audit (mandatory):**
```bash
grep -rE "free to use|public domain|is used by|definitely used" \
  backend/app/email/ \
  backend/app/ai/weekly_digest.py \
  backend/app/ai/prompts/weekly_digest_v1.md \
  backend/app/tasks/send_instant_alert.py \
  backend/app/tasks/send_weekly_digest.py \
  frontend/src/app/account/ \
  frontend/src/app/login/
```
Must return zero matches.

**Send-mode guard test:**
- Boot the app with `EMAIL_SEND_MODE=production` and an empty
  `RESEND_API_KEY` → app refuses to start (sanity check).
- Boot with no `EMAIL_SEND_MODE` → defaults to `dev`.
- Test that switching to `production` requires `EMAIL_PRODUCTION_ACKNOWLEDGED=true` env var (explicit user opt-in).

**Acceptance:**
- All new test modules pass.
- Full `pytest -q` (no `--ignore`) — count reported vs baseline (227).
- Frontend `npm run build` clean.
- Language audit returns zero matches.
- Send-mode default is `dev`. Production mode requires explicit
  acknowledgement env var.

---

## Files Summary

| Created | Count | Modified | Count |
|---|---|---|---|
| Backend migrations | 3 | `core/models.py` | +ORM imports |
| Backend modules | 9 | `api/v1/router.py` | +2 routes |
| Backend tests | 8 | `api/deps.py` | +current_user |
| Backend prompt | 1 | `tasks/theme_matcher.py` | +hook |
| Frontend pages | 4 | `tasks/celery_app.py` | +tasks + beat |
| Frontend modules | 1 | `app/themes/[id]/page.tsx` | +subscribe panel |
| Email templates | 3 | `lib/api.ts`, `lib/types.ts` | +endpoints + types |
| **Total new** | **~30 files** | **Total modified** | **~10 files** |

---

## Reporting rules (carried forward from Sprint 5)

- Every chunk reports verification with exact pytest count, baseline diff.
- No "✅" without numbers attached.
- DEVIATION DETECTED protocol: if implementation diverges from this
  plan, stop and present Options A/B/C with recommendation; do not
  silently work around.
- The user commits; the implementer does not run git commands.
- Browser smoke test required for any frontend chunk before marking
  done — load the affected pages, describe rendered state.

---

## Pre-flight checks before Chunk 1

- [ ] User has obtained Resend API key (free tier) and set
  `RESEND_API_KEY` in `.env`.
- [ ] User has decided on `EMAIL_FROM_ADDRESS` (e.g.
  `alerts@<your-domain>`); domain must be verified in Resend
  dashboard before any production sends.
- [ ] `EMAIL_DEV_RECIPIENT` env var set to the email that should
  receive all dev-mode messages.
- [ ] `AUTH_SECRET_KEY` set (32+ random bytes, base64).

If any of these are missing, the user should resolve them before
implementation begins. Document the resolved values in
`.env.example` (without secret values).
