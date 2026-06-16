# Resend Health Investigation — June 2026

## Root Cause Hypothesis

**The health check was calling `https://api.resend.com/domains` which requires `full_access` permission.** The actual email sender uses `resend.Emails.send` which only needs `sending_access`. If the Resend API key was created with `sending_access` (the recommended permission for production), the `/domains` health probe returns 403 even though email sending works correctly.

This means: the key is probably fine for sending emails, but the health check was testing the wrong thing.

## Fix Applied

**File:** `backend/app/api/health.py` — `_check_resend()`

**Change:** `https://api.resend.com/domains` → `https://api.resend.com/emails?limit=1`

The `/emails` endpoint works with `sending_access` keys. It lists recently sent emails (empty list for new accounts). This correctly tests whether the API key is valid and has send capability.

## Env Vars Required

| Var | Purpose | Notes |
|-----|---------|-------|
| `RESEND_API_KEY` | API key (sending_access recommended) | Pydantic strips whitespace automatically |
| `EMAIL_FROM_ADDRESS` | Verified sender domain | Must match a domain verified in Resend dashboard |
| `EMAIL_SEND_MODE` | `dev` / `dry_run` / `production` | Defaults to `dev` |
| `EMAIL_PRODUCTION_ACKNOWLEDGED` | Must be `"true"` for production mode | Blocks accidental production sends |
| `EMAIL_DEV_RECIPIENT` | Redirect address in dev mode | Email goes here instead |

## Safe Diagnostic Commands

Do NOT print or commit the API key. Run these on the production server.

```bash
# 1. Check key exists and is non-empty (hides the actual value)
docker compose exec backend python -c "
from app.config import settings
key = settings.resend_api_key
print(f'Key length: {len(key)}')
print(f'Key prefix: {key[:6]}...')
print(f'Has quotes: {key.startswith(\"re_\") == False}')  # Resend keys start with re_
print(f'From address: {settings.email_from_address}')
print(f'Send mode: {settings.email_send_mode}')
print(f'Production ack: {settings.email_production_acknowledged}')
"

# 2. Test the key with the /emails endpoint (sending_access works)
docker compose exec backend python -c "
import urllib.request
from app.config import settings
req = urllib.request.Request(
    'https://api.resend.com/emails?limit=1',
    headers={'Authorization': f'Bearer {settings.resend_api_key}'},
)
try:
    resp = urllib.request.urlopen(req, timeout=5)
    print(f'OK — HTTP {resp.getcode()}')
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.reason}')
except Exception as e:
    print(f'Error: {e}')
"

# 3. Test sending a simple email (dev mode — won't send to real user)
docker compose exec backend python -c "
from app.config import settings
print(f'From: {settings.email_from_address}')
print(f'Mode: {settings.email_send_mode}')
print(f'Dev recipient: {settings.email_dev_recipient or \"(not set — would go to real user)\"}')
"
```

## Sender Domain Check

If the key passes the `/emails` test but emails fail to send, check that `EMAIL_FROM_ADDRESS` exactly matches a domain verified in the Resend dashboard (https://resend.com/domains). Subdomains must be verified separately. For example:
- `verified@inventionindex8.com` ≠ `verified@sending.inventionindex8.com`
- The domain in `EMAIL_FROM_ADDRESS` must appear in the Resend domains list exactly.

## Key Permissions

| Permission | Can send email? | Can call /domains? | Can call /emails? |
|-----------|----------------|-------------------|-------------------|
| `full_access` | ✅ | ✅ | ✅ |
| `sending_access` | ✅ | ❌ (403) | ✅ |

**Recommended:** Use `sending_access` for production (principle of least privilege). The fix above makes the health check compatible.

## Action Items

1. Pull latest (includes health.py fix)
2. Rebuild backend
3. Run diagnostic command #1 first
4. If key looks valid: run #2 (test /emails endpoint)
5. If /emails returns OK: health should show `resend: ok`
6. If still fails: the key may actually be invalid/revoked — create a new `sending_access` key at resend.com
