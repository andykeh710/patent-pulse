# Redis Security Hardening Runbook

**Incident:** Hetzner flagged Redis on `188.245.85.248` as publicly accessible on port 6379.
**Priority:** P0 — fix immediately. Assume possible compromise until verified clean.
**Date:** 2026-06-12

---

## Root Cause

`docker-compose.yml` line 22 had `"6379:6379"` (binds to `0.0.0.0`). The production override
(`docker-compose.prod.yml`) sets `ports: []` for Redis, but if the stack was ever started
without the prod override file, Redis was exposed to the internet. Additionally, no
`--requirepass` was configured — Redis was running with zero authentication.

---

## Immediate Actions (execute in order)

### Step 1: SSH in and verify the exposure

```bash
ssh root@188.245.85.248
sudo ss -ltnp | grep ':6379'
```

If you see `0.0.0.0:6379`, Redis is exposed publicly. If you see `127.0.0.1:6379`, the
fix may already be applied (the prod override `ports: []` might be active).

### Step 2: Block port 6379 at the firewall level (belt + suspenders)

```bash
# UFW (if running)
sudo ufw allow OpenSSH
sudo ufw deny 6379/tcp
sudo ufw reload
sudo ufw status verbose

# If UFW not enabled:
sudo ufw enable
```

**Also check Hetzner Cloud Firewall / Robot Firewall** in the Hetzner web console.
Add a rule: **Deny inbound TCP port 6379 from 0.0.0.0/0**.

### Step 3: Redeploy with the fixed config

```bash
cd /opt/invention-index-8

# Pull latest (contains the fixed docker-compose.yml with 127.0.0.1 binding + requirepass)
git pull origin main

# Set a strong Redis password in .env (ONE-TIME — never commit to repo)
echo 'REDIS_PASSWORD=CHANGE_THIS_TO_64_RANDOM_CHARS' >> .env

# Redeploy
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Step 4: Verify from outside

```bash
# From your local machine (NOT the server):
nc -vz 188.245.85.248 6379
```

Expected output: **`Connection refused`** or **`timed out`**. If it still connects, port 6379
is still exposed — check the Hetzner firewall rules.

### Step 5: Check Redis for suspicious activity

```bash
# Connect locally (only works from server now with 127.0.0.1 binding)
docker compose exec redis redis-cli --pass $REDIS_PASSWORD

# Check keyspace
INFO keyspace

# Scan keys (if many keys, use SCAN instead of KEYS)
SCAN 0 COUNT 100

# Look for: unknown session keys, unauthorized cron payloads, modified app state
# Normal keys: chat:conv:*, chat:quota:*
# Suspicious: anything you didn't put there

# Check logs
docker compose logs redis | tail -200
sudo journalctl -u redis-server --since "2026-06-09" 2>/dev/null
```

### Step 6: Rotate secrets

Rotate EVERYTHING that touches or was referenced in Redis:

1. **[ ] Redis password** — already set via new `REDIS_PASSWORD` in .env
2. **[ ] AUTH_SECRET_KEY** — generates new JWT signing key. All users logged out (acceptable).
3. **[ ] Resend API key** — rotate in Resend dashboard, update .env, redeploy
4. **[ ] Stripe API keys** — rotate in Stripe dashboard if webhook secrets or test keys were in Redis
5. **[ ] Any other secrets in .env that were also referenced in Redis**

Then redeploy:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate backend worker beat
```

---

## What was fixed in code

### docker-compose.yml changes (committed in this PR):

1. **Port binding:** `"6379:6379"` → `"127.0.0.1:6379:6379"` — Redis only accepts local connections
2. **Authentication:** Added `--requirepass ${REDIS_PASSWORD:-redis-dev-password}` to Redis command
3. **REDIS_URL updated:** All 3 service environments now use `redis://:${REDIS_PASSWORD}@redis:6379/0`
4. **Healthcheck:** Updated to `redis-cli --pass $REDIS_PASSWORD ping`

### Production override (docker-compose.prod.yml):

Already had `ports: []` for Redis — this removes ALL host port exposure in production.
Combined with the new `127.0.0.1` binding in base, double protection.

---

## What to tell Hetzner

Reply to Hetzner support email:

> Thank you for the notification. We have secured the Redis instance on 188.245.85.248 by:
> - Blocking public access to port 6379 via UFW and Hetzner firewall
> - Binding Redis to 127.0.0.1 only (no external interface exposure)
> - Enabling Redis authentication with a strong password
> - Removing port exposure from Docker configuration
> - Rotating all credentials that may have been accessible
> We have reviewed Redis state and found [no evidence of / some evidence of — pick one] unauthorized access.

---

## Verification checklist

- [ ] `nc -vz 188.245.85.248 6379` → connection refused
- [ ] `docker compose logs redis | head -5` → shows `requirepass` active
- [ ] `curl https://inventionindex8.com/health` → 200 OK (app still works)
- [ ] Chat functionality tested: send a message, confirm response
- [ ] Weekly briefing generation still works (check Celery beat logs)
- [ ] Hetzner Cloud firewall rule added for port 6379
