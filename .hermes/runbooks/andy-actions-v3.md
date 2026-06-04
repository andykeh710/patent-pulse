# Andy Actions — V3 Launch Checklist

Items that require manual action from Andy — cannot be automated by Hermes.

## 🔴 Tier 0 — Do NOW

### Rotate Resend API Key (leaked in chat)
1. Go to https://resend.com/api-keys
2. Revoke the old key
3. Generate a new key
4. Update on server:
   ```bash
   ssh root@188.245.85.248
   vi /opt/invention-index-8/app.env
   # Replace RESEND_API_KEY=re_... with new key
   docker compose up -d --force-recreate backend
   ```

### UptimeRobot Monitor
1. Sign up at https://uptimerobot.com (free tier)
2. Add HTTPS monitor for `https://inventionindex8.com`
3. Add keyword monitor for `https://inventionindex8.com/api/v1/health` expecting `"overall":"ok"`
4. Alert to andy@web3r.tech

### Deploy Production Build
After pushing the latest commits:
```bash
ssh root@188.245.85.248 "cd /opt/invention-index-8 && git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build frontend"
```

### Verify Backup
```bash
ssh root@188.245.85.248 "cd /opt/invention-index-8 && docker compose exec backend python -c \"
from app.tasks.backup import backup_database_daily
result = backup_database_daily()
print(result)
\""
```

---

## 🟡 Tier 1 — Do This Week

### Stripe Business Verification
1. Go to https://dashboard.stripe.com/account
2. Complete: EIN/SSN, business address, bank account, phone
3. Takes 1-3 business days

### DNS for Email Deliverability (Resend)
Add to Cloudflare DNS:
| Type | Name | Value |
|------|------|-------|
| TXT | inventionindex8.com | `v=spf1 include:spf.resend.com -all` |
| TXT | resend._domainkey | (from Resend dashboard → Domains → your domain → DNS records) |
| TXT | _dmarc | `v=DMARC1; p=none; rua=mailto:andy@web3r.tech` |

### Sentry DSNs on Server
1. Get DSNs from https://sentry.io (create free account if needed)
2. Add to `/opt/invention-index-8/app.env`:
   ```
   SENTRY_DSN=https://xxx@sentry.io/xxx
   NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/xxx
   ```

### Test DB Restore Drill
```bash
ssh root@188.245.85.248 "cd /opt/invention-index-8 && docker compose exec db pg_dump -U patent patent_pulse | gzip > /tmp/test_restore.sql.gz"
# Then follow restore runbook: .hermes/runbooks/restore-db.md
```

---

## 🟢 Tier 2 — Before Launch

### Stripe LIVE Mode
1. Create Live products with lookup keys: ii8_free, ii8_basic_yearly, ii8_lifetime, ii8_enterprise_yearly
2. Create Live webhook at `https://inventionindex8.com/api/v1/billing/webhook`
3. Get Live keys (DO NOT add to .env yet — park in password manager)
4. When ready: flip `STRIPE_API_KEY` to `sk_live_` and `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` to `pk_live_`

### Test Weekly Briefing Email
1. After frontend is deployed:
   ```bash
   docker compose exec backend python -c "
   import asyncio
   from app.tasks.send_weekly_digest import _fan_out_async
   asyncio.run(_fan_out_async())
   "
   ```
2. Check andy@web3r.tech inbox
3. In dev mode, subject will show `[DEV → ...]` prefix — review formatting
