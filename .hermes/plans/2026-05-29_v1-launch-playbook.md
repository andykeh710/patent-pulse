# Patent Pulse V1 — Launch Playbook

Copy-paste-ready steps to get from "code complete" to "first paying
customer." ~1-2 days of focused work. Mark each ✅ as you complete it.

## Recommended stack (defaults for this playbook)

| Service | Pick | Why |
|---|---|---|
| Hosting (app + worker + beat) | **Railway** | Single platform for app + DB + Redis, auto-detects Dockerfile, ~$5-20/mo |
| Postgres + pgvector | **Supabase Free** | pgvector built-in, daily backups included, free tier covers V1 |
| Redis | **Upstash Free** | Serverless, works over public network, 10K commands/day free |
| Domain registrar | **Cloudflare Registrar** | At-cost pricing, free WHOIS privacy, DNS in same dashboard |
| Email | **Resend** | Already wired in Sprint 6 |
| Errors | **Sentry Free** | 5K errors/month free |

Alternative if you prefer Fly.io: doable but more steps (separate Fly Postgres, separate Upstash, separate volumes). Railway is the fastest path to V1.

---

## ⏱ Phase A — Account setup (do these in parallel, ~30 min total)

### A1. Sign up for Railway
- URL: https://railway.app
- Connect GitHub, authorize access to `andykeh710/patent-pulse`
- ✅ Done when you can see your repos in Railway

### A2. Sign up for Supabase
- URL: https://supabase.com
- Create a new project — pick a region close to your customers (e.g. `us-east-1`)
- Set a strong DB password (save in password manager)
- ✅ Done when project is provisioned (~2 min)

### A3. Sign up for Upstash
- URL: https://console.upstash.com
- Create a Redis database — same region as Supabase
- Type: **Regional** (not Global, cheaper for V1)
- ✅ Done when you see the connection URL

### A4. Sign up for Sentry
- URL: https://sentry.io
- Create org + 2 projects: `patent-pulse-backend` (Python) and `patent-pulse-frontend` (Next.js)
- ✅ Done when you have both DSN URLs (copy them to a scratch file)

### A5. Decide on domain
- Pick a name (e.g. `patentpulse.io`, `patentpulse.app`, `getpatentpulse.com`)
- Register at Cloudflare Registrar: https://dash.cloudflare.com → Domain Registration → Register
- ✅ Done when domain is in your Cloudflare account

---

## ⏱ Phase B — Stripe + Resend dashboards (~45 min)

### B1. Stripe Test Mode setup

```
URL: https://dashboard.stripe.com
1. Top-right toggle to "Test mode" (orange)
2. Developers → API keys → reveal Secret key
   → copy the sk_test_... value (save for env)
3. Products → + Add product:
   Name: "Basic"        Pricing: $8 / year recurring
   Name: "Lifetime"     Pricing: $108 one-time
   Name: "Enterprise"   Pricing: $1000 / year recurring
4. For each product, copy the Price ID (price_...) — save 3 values
5. Developers → Webhooks → + Add endpoint
   Endpoint URL: https://api.YOURDOMAIN.com/api/v1/billing/webhook
   (you'll fix the URL after deploy; for now use placeholder)
   Events to send (5):
     checkout.session.completed
     invoice.payment_succeeded
     invoice.payment_failed
     customer.subscription.deleted
     customer.subscription.updated
   → Add endpoint
6. Click the new endpoint → Reveal "Signing secret" → copy whsec_...
```

✅ You should now have:
- STRIPE_API_KEY=sk_test_...
- STRIPE_WEBHOOK_SECRET=whsec_...
- STRIPE_PRICE_ID_BASIC=price_...
- STRIPE_PRICE_ID_LIFETIME=price_...
- STRIPE_PRICE_ID_ENTERPRISE=price_...

### B2. Resend domain setup

```
URL: https://resend.com
1. Domains → + Add Domain → enter your domain (e.g. patentpulse.io)
2. Resend will show 3-4 DNS records (SPF, DKIM, optionally DMARC, optionally
   MX for inbound). Copy them.
3. In Cloudflare → DNS → add the records exactly as shown
4. Back in Resend, click "Verify" — may take 5-30 min for DNS propagation
5. API Keys → + Create API Key → name it "production", copy re_...
```

✅ You should now have:
- RESEND_API_KEY=re_...
- EMAIL_FROM_ADDRESS=alerts@yourdomain.com (or any address on the verified domain)

### B3. Generate secrets locally

```bash
# Run these on your laptop, save the outputs:
openssl rand -base64 32  # → AUTH_SECRET_KEY
```

✅ You should now have:
- AUTH_SECRET_KEY=<32-byte base64 string>

---

## ⏱ Phase C — Provision Postgres + Redis URLs (~15 min)

### C1. Supabase Postgres URL
```
URL: https://supabase.com/dashboard/project/YOUR_PROJECT/settings/database
1. Connection string → "URI" tab → copy
2. Replace [YOUR-PASSWORD] in the URL with your actual DB password
3. You'll get something like:
   postgresql://postgres:PASSWORD@db.XXXXX.supabase.co:5432/postgres
```

Convert to async format for Patent Pulse:
- DATABASE_URL: `postgresql+asyncpg://postgres:PASSWORD@db.XXXXX.supabase.co:5432/postgres`
- DATABASE_URL_SYNC: `postgresql+psycopg2://postgres:PASSWORD@db.XXXXX.supabase.co:5432/postgres`

### C2. Enable pgvector on Supabase
```
URL: https://supabase.com/dashboard/project/YOUR_PROJECT/database/extensions
Search "vector" → toggle ON
```

### C3. Upstash Redis URL
```
URL: https://console.upstash.com/redis
Click your database → "REST API" tab is NOT what we want
Use the regular Redis URL from the "Details" section:
  rediss://default:PASSWORD@your-name.upstash.io:6379
```

REDIS_URL: `rediss://default:PASSWORD@your-name.upstash.io:6379`
(Note: `rediss://` with double-s = TLS, required by Upstash)

---

## ⏱ Phase D — Deploy to Railway (~1-2 hours)

### D1. Create Railway project

```
URL: https://railway.app/new
1. "Deploy from GitHub repo" → select patent-pulse
2. Railway will detect the Dockerfile in backend/ — confirm
3. Railway names the service "patent-pulse" — rename to "backend"
4. Service Settings → Build → Root Directory: backend/
5. Don't deploy yet — set env vars first (step D2)
```

### D2. Add env vars to Railway

```
In the backend service → Variables tab → "Raw Editor" → paste:

DATABASE_URL=postgresql+asyncpg://postgres:PASS@db.XXXX.supabase.co:5432/postgres
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:PASS@db.XXXX.supabase.co:5432/postgres
REDIS_URL=rediss://default:PASS@your-name.upstash.io:6379
AUTH_SECRET_KEY=<your base64 string>
MAGIC_LINK_BASE_URL=https://YOURDOMAIN.com
RESEND_API_KEY=re_...
EMAIL_FROM_ADDRESS=alerts@YOURDOMAIN.com
EMAIL_DEV_RECIPIENT=you@YOURDOMAIN.com
EMAIL_SEND_MODE=dev
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_BASIC=price_...
STRIPE_PRICE_ID_LIFETIME=price_...
STRIPE_PRICE_ID_ENTERPRISE=price_...
ANTHROPIC_API_KEY=<your key>
OPENAI_API_KEY=<your key>
USPTO_API_KEY=<your key>
SENTRY_DSN=<backend DSN from Sentry>
ENVIRONMENT=production
CELERY_WORKER=false
```

NOTE: Keep `EMAIL_SEND_MODE=dev` for now. We flip to production after smoke test.

### D3. Deploy backend service
```
Railway → Deploy
Wait ~5 min for first build
Watch logs: if you see "Uvicorn running on 0.0.0.0:8000" → good
If errors: most common is missing env var (Railway will tell you)
```

### D4. Run alembic migrations
```
Railway → Service Settings → Custom Start Command:
Temporarily change to: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
Redeploy → wait for logs to show "Running upgrade ... 0020"
Then revert the start command to just: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

(Alternative: Railway → Settings → "One-off Job" → run `alembic upgrade head` once)

### D5. Add worker service
```
Railway → + New Service → GitHub repo (same)
Name: "worker"
Build root: backend/
Custom Start Command: celery -A app.tasks.celery_app worker --loglevel=info
Add env vars: same as backend BUT set CELERY_WORKER=true
Deploy
```

### D6. Add beat service
```
Railway → + New Service → GitHub repo (same)
Name: "beat"
Build root: backend/
Custom Start Command: celery -A app.tasks.celery_app beat --loglevel=info
Add env vars: same as backend with CELERY_WORKER=true
Deploy
```

### D7. Add frontend service
```
Railway → + New Service → GitHub repo (same)
Name: "frontend"
Build root: frontend/
Railway will detect Next.js
Add env vars:
  NEXT_PUBLIC_API_BASE_URL=https://api.YOURDOMAIN.com
  NEXT_PUBLIC_SENTRY_DSN=<frontend DSN from Sentry>
  NEXT_PUBLIC_ENVIRONMENT=production
Deploy
```

### D8. Wire domain
```
Backend service → Settings → Networking → "Custom Domain"
Add: api.YOURDOMAIN.com
Railway gives you a CNAME target
Cloudflare → DNS → add CNAME: api → <railway target>, Proxied OFF
Wait 1-2 min for SSL provisioning

Frontend service → same flow → custom domain: YOURDOMAIN.com (and www.YOURDOMAIN.com)
Add A record in Cloudflare pointing root to Railway → enable proxy
```

### D9. Update Stripe webhook URL
```
Stripe dashboard → Developers → Webhooks → click your endpoint
Edit → URL: https://api.YOURDOMAIN.com/api/v1/billing/webhook
Save
```

---

## ⏱ Phase E — Smoke test (~30 min)

Run each step against the production URL. Document any failures.

### E1. Health check
```bash
curl https://api.YOURDOMAIN.com/health | python3 -m json.tool
# Expect: {db: ok, redis: ok, resend: ok, overall: ok}
```

### E2. Magic-link sign-in
```
Open https://YOURDOMAIN.com → click Sign In
Enter your email → submit
Check inbox at EMAIL_DEV_RECIPIENT (dev-mode rewrites recipient)
Subject should start with [DEV → your-real-email@...]
Click the link → should land you logged in at /account
```

### E3. Subscribe + alert flow
```
Go to /themes → click any topic
Subscribe with mode=instant_alert
Wait for theme matcher to fire (or trigger manually via Railway logs)
Confirm an alert email arrives at EMAIL_DEV_RECIPIENT
```

### E4. Stripe checkout (test mode)
```
/account/billing → click Upgrade to Basic
Stripe checkout opens — use test card: 4242 4242 4242 4242, any future expiry, any CVC
Complete → redirected back to /account/billing?success=true
Check the user's tier in Railway logs OR via curl:
  curl -b "auth_session=YOUR_COOKIE" https://api.YOURDOMAIN.com/api/v1/billing/subscription
Should show tier=basic
```

### E5. Export endpoints
```
With your basic-tier cookie:
  curl -b "auth_session=COOKIE" https://api.YOURDOMAIN.com/api/v1/exports/expiry.csv -o test.csv
  head test.csv
```

### E6. GDPR delete
```
/account → scroll to Danger Zone → Delete account
Type your email to confirm → submit
Should be logged out and redirected to /
Verify the user is gone:
  curl -b "auth_session=COOKIE" https://api.YOURDOMAIN.com/api/v1/auth/me
  → expect 401
```

---

## ⏱ Phase F — Production switch (~5 min)

When all of E1-E6 pass:

### F1. Flip email send mode
```
Railway → backend service → Variables
Change: EMAIL_SEND_MODE=production
Add:    EMAIL_PRODUCTION_ACKNOWLEDGED=true
Redeploy (Railway auto-redeploys on var change)
```

### F2. Verify production-mode startup
```
Railway logs → should NOT see "Sentry disabled" if Sentry is set
Should see normal Uvicorn boot
Hit /health → still all green
```

### F3. Send yourself a real magic link
```
/login → enter your real email → submit
Inbox: subject should NO LONGER have [DEV → ...] prefix
This is a real production send.
```

### F4. Tag v1.0.0
```bash
git tag -a v1.0.0 -m "Patent Pulse V1 — first production release"
git push origin v1.0.0
```

🚀 **You are live.**

---

## Going-live optional polish (can do post-launch)

| Item | Effort |
|---|---|
| Sentry source map upload on deploy (Railway → Build Hook to upload sourcemaps) | 30 min |
| Set `RELEASE_SHA` to git SHA in deploy → Sentry release tagging | 15 min |
| Stripe live mode (when ready for real money) — needs code change to remove the `sk_live_` refuse-gate | 1 hour |
| Status page (Better Stack / Atlassian Statuspage) | 1 hour |
| Customer support email forwarding (e.g. support@yourdomain → your inbox) | 30 min |
| Cookie banner (only if you add analytics) | 1 hour |
| Onboarding flow polish (3-step wizard after first sign-in) | 2 hours |

---

## If something breaks

| Symptom | First thing to check |
|---|---|
| Health endpoint returns degraded | Railway logs of backend service for which probe failed |
| Migrations didn't run | Run alembic upgrade head as one-off job |
| Stripe webhook signature invalid | Webhook secret in Railway env doesn't match Stripe dashboard |
| Magic link email not arriving | Resend dashboard → Logs → look for the send attempt |
| 401 on every endpoint | AUTH_SECRET_KEY changed between sign-in and request → re-issue cookie |
| Worker tasks not firing | Beat service is down OR Redis URL wrong in worker/beat env |
| pgvector queries fail | Extension not enabled in Supabase (Phase C2) |

## Cost estimate for V1 traffic (~10 users)

| Service | Plan | Monthly |
|---|---|---|
| Railway (3 services: backend, worker, beat, frontend) | Hobby + usage | ~$20 |
| Supabase | Free | $0 |
| Upstash | Free | $0 |
| Sentry | Developer (free) | $0 |
| Cloudflare domain | At-cost | $9/year |
| Resend | Free (3K/mo) | $0 |
| Stripe | Test mode | $0 |
| **Total** | | **~$20/mo + $9/year** |

When you scale past free tiers (~100 users), Supabase Pro is $25/mo and Upstash Pro is ~$10/mo. Still under $60/mo through ~500 paying users.
