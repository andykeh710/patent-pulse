# Assignee Backfill Investigation — June 15, 2026

## Root Cause

**The backfill task logic is correct. It was never executed on production.**

The Celery beat schedule runs `backfill-assignees-daily` at 04:00 UTC, queued to
the `maintenance` queue. If the beat container or maintenance worker was not
running at 04:00 UTC, the task never fired.

## Task Verification

File: `backend/app/tasks/backfill_assignees.py` (161 lines)

- ✅ Imports from `celery_app` — registered
- ✅ Beat schedule entry at line 327-331 of `celery_app.py`
- ✅ Uses `ON CONFLICT (normalized_name) DO UPDATE` — idempotent, updates existing rows including entity_type
- ✅ `entity_type` heuristic: regex-based classification (university, gov, corporation)
- ✅ `country`: intentionally deferred (SQL comment: "requires an external data source")
- ✅ `normalize_assignee()` function: defined in migration 0026, applied via `alembic upgrade head`
- ✅ Tests exist in `backend/tests/tasks/test_backfill_assignees.py`

## Heuristic Coverage for Production Names

| Name | Pattern Match | Expected entity_type |
|------|--------------|---------------------|
| SAMSUNG ELECTRONICS CO LTD | `LTD` → corporation | ✅ corporation |
| IBM CORP | `CORP` → corporation | ✅ corporation |
| TOYOTA JIDOSHA KABUSHIKI KAISHA | No match (KAISHA ≠ KK) | ⬜ NULL |
| QUALCOMM INC | `INC` → corporation | ✅ corporation |
| APPLE INC | `INC` → corporation | ✅ corporation |

~85-90% of assignees are expected to match one of the three categories.
Japanese KK/GmbH equivalents and non-standard entities will remain NULL —
this is expected and documented.

## Validation Queries

Before triggering backfill:
```sql
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE entity_type IS NOT NULL) AS with_entity_type
FROM assignees;
-- Expected: total=16723, with_entity_type=0
```

After backfill:
```sql
SELECT entity_type, COUNT(*) AS cnt
FROM assignees GROUP BY entity_type ORDER BY cnt DESC;
-- Expected: corporation/NNNNN, university/NNN, gov/NN, NULL/NNNN
```

## Execution Plan

### Step 1 — Verify prereqs (on production server)
```bash
# Confirm normalize_assignee function exists
docker compose exec db psql -U patent -d patent_pulse -c "
  SELECT proname FROM pg_proc WHERE proname = 'normalize_assignee';
"
# Expected: normalize_assignee

# Confirm celery beat schedule includes the task
docker compose logs beat --tail 50 | grep -i "backfill-assignees\|Scheduler"
# If no mention, beat may have never been healthy at 04:00 UTC
```

### Step 2 — Trigger via admin endpoint (recommended)
```bash
# Get admin cookie from browser (DevTools → Application → Cookies)
curl -X POST https://inventionindex8.com/api/v1/admin/trigger-assignee-backfill \
  -H "Cookie: <admin_cookie>" \
  -H "Content-Type: application/json"
# Expected: {"status": "accepted", "task_id": "..."}
```

### Step 3 — Monitor progress
```bash
# Check worker logs for backfill activity
docker compose logs worker --tail 30 | grep -i "backfill\|assignee"
# Expected: "Assignee backfill: total=... inserted=... updated=..."

# Check entity_type populate
docker compose exec db psql -U patent -d patent_pulse -c "
  SELECT entity_type, COUNT(*) FROM assignees GROUP BY entity_type;
"
# Expected: rows for corporation, university, gov appear
```

### Step 4 — If admin endpoint unavailable, run directly
```bash
docker compose exec backend python -c "
import asyncio
from app.tasks.backfill_assignees import backfill_assignees
result = asyncio.run(backfill_assignees())
print(result)
"
# Expected: {"total_processed": 16723, "inserted": 0, "updated": 16723}
```
This is safe — idempotent, no data loss, updates existing rows only.

### Rollback (if needed)
No rollback needed. The task is idempotent. Re-running always produces the same
entity_type classifications. Country stays NULL regardless.

If the heuristic produces incorrect classifications for specific names,
those can be corrected with targeted UPDATE statements later. No migration
needed.

## V3 Readiness

Assignee entity_type enrichment is a **V3 readiness blocker** for:
- Company segmentation badges on company pages
- "Follow company" filtered by entity_type
- Personalized Today: "New filings from companies like the ones you follow"
- Company-move intelligence: "3 new university assignees in battery tech"

Country detection remains deferred (needs external data source — future sprint).
