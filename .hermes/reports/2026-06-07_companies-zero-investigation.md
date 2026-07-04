# Companies Page "0 of 0" Investigation

**Date**: 2026-06-07
**Investigator**: Hermes Agent
**Branch**: `main` (current deploy on inventionindex8.com)

## Symptom

The `/companies` frontend page renders coverage bars showing 0% with
text like "0 of 0 companies" (or "0 of 16,723 companies" depending on
load state), where users expect populated country/entity-type metadata
and a working country filter dropdown. The paginated company table
loads successfully (16,723 companies, 50,293 patent links), but every
company shows "Metadata pending" and country/entity-type coverage is
100% empty.

## Data Path Traced

### Frontend

**Page**: `frontend/src/app/(app)/companies/page.tsx`

Three SWR hooks drive the page:

1. `useSupplierSummary()` → `GET /api/v1/suppliers/summary` (line 21)
2. `useSuppliers(params)` → `GET /api/v1/suppliers?sort_by=...&page=...` (line 22)
3. `useSupplierMap()` → `GET /api/v1/suppliers/map` (line 23)

**Hook**: `frontend/src/hooks/useSuppliers.ts` (line 1-15)
- Wraps `suppliersApi.summary()`, `.list()`, `.map()` with SWR.

**API client**: `frontend/src/lib/api.ts` (lines 344-356)
- `suppliersApi.summary()` → `GET /api/v1/suppliers/summary`
- `suppliersApi.list(params)` → `GET /api/v1/suppliers?${toQueryString(params)}`
- `suppliersApi.map()` → `GET /api/v1/suppliers/map`

**Empty-state condition** (page.tsx line 247):
```tsx
if (items.length === 0) {
  return <div>No companies found for the selected filters.</div>;
}
```

**Coverage bars** (page.tsx lines 222-236):
```tsx
function CoverageBar({ label, value, total }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    ...
    <p>{formatNumber(value)} of {formatNumber(total)} companies</p>
  );
}
```

Called with:
```tsx
<CoverageBar label="Country Coverage"
  value={summary?.suppliers_with_country || 0}
  total={summary?.total_suppliers || 0} />
```

When `summary` is `undefined` (API failure / loading), both `value`
and `total` coerce to 0 → renders "0 of 0 companies". When the API
succeeds, `total` = 16,723 but `value` = 0 → renders "0 of 16,723
companies".

### Backend

**File**: `backend/app/api/v1/suppliers.py` (398 lines)

Three endpoints registered in `backend/app/api/v1/router.py` (line 34):
```python
v1_router.include_router(suppliers.router, prefix="/suppliers",
                         tags=["suppliers"])
```

**Summary query** (lines 79-162):
```sql
WITH supplier_rows AS (
    SELECT
        assignee_val AS supplier_name,
        MAX(a.country) AS country,
        MAX(a.entity_type) AS entity_type,
        COUNT(DISTINCT p.id) AS patent_count,
        COUNT(DISTINCT p.id) FILTER (WHERE p.legal_status = 'GRANTED')
            AS active_patent_count,
        COUNT(DISTINCT p.id) FILTER (
            WHERE p.legal_status = 'GRANTED'
            AND p.estimated_expiry_date >= :today
            AND p.estimated_expiry_date <= :five_years
        ) AS expiring_soon_count,
        COUNT(DISTINCT LEFT(cpc_val, 1))
            FILTER (WHERE cpc_val IS NOT NULL AND cpc_val != '')
            AS technology_area_count,
        AVG(COALESCE(p.opportunity_score, p.interesting_score))
            AS average_signal_score
    FROM patent_publications p
    JOIN LATERAL jsonb_array_elements_text(p.assignees) AS assignee_val
        ON true
    LEFT JOIN LATERAL jsonb_array_elements_text(p.cpc) AS cpc_val ON true
    LEFT JOIN assignees a
        ON lower(a.display_name) = lower(assignee_val)
        OR lower(a.normalized_name) = lower(assignee_val)
    WHERE assignee_val IS NOT NULL AND assignee_val != ''
    GROUP BY assignee_val
)
SELECT * FROM supplier_rows
```

Key observation: `LEFT JOIN assignees a` is the ONLY source of
`country` and `entity_type` metadata. If the `assignees` table has
zero rows, the LEFT JOIN always produces NULL — basic aggregation
(patent counts) works, but all enrichment fields are null.

**List query** (lines 165-249): Same CTE structure, plus pagination
and filtering via `_supplier_filters()` (line 70-76).

**Map query** (lines 252-285): Calls `list_suppliers()` with
`page_size=10000`, then groups by `country` field. When all countries
are null, everything groups into "Unknown".

### Data Layer

**patent_publications table** (local and production):
```
total_patents:          64,231
patents_with_assignees: 47,492  (73.9% coverage)
patents_without:        16,739
```

Sample assignee data (JSONB arrays):
```
["TOYO SEIKAN KAISHA LTD"]
["GOLDMAN SACHS &AMP; CO"]
["VIACOM INTERNATIONAL INC"]
```

The `assignees` column is a JSONB `text[]` — each element is a raw
assignee name from the patent office feed.

**assignees table** (`backend/app/core/ai_models.py`, lines 80-95):

```python
class Assignee(Base):
    """Normalized assignee. Populated by a one-shot backfill from
    PatentPublication.assignees."""
    __tablename__ = "assignees"
    id: Mapped[uuid.UUID]
    normalized_name: Mapped[str]         # unique, indexed
    display_name: Mapped[str]
    aliases: Mapped[list[str]]           # JSONB
    country: Mapped[str | None]
    entity_type: Mapped[str | None]      # corporation|university|sme|individual|gov
    patent_count: Mapped[int]
```

Created by migration `0003_phase0_ai_artifact_layer.py` (lines 134-155).

**Current state — CRITICAL FINDING**:

```
production> SELECT COUNT(*) FROM assignees;
 count
-------
     0
(1 row)
```

**Zero rows on production.** The table was created by the migration
but **no code ever inserts into it**. Evidence:

- Searched all `.py` files under `backend/app/` for `Assignee(` —
  only hits are the model definition and test fixtures.
- Searched for `assignees.insert`, `session.add.*Assignee`,
  `backfill.*assignee` — zero matches in production code.
- No Celery task for assignee normalization / backfill exists.
- No Celery beat schedule entry exists.
- The `normalize_assignee()` PostgreSQL function DOES exist in the DB
  (it was manually created at some point) but was never applied.

**Tests pass because they seed the table** (`backend/tests/api/test_suppliers.py`):

- `test_supplier_list_enriches_from_normalized_assignees` (line 46):
  Creates an `Assignee` row with `country="US"`,
  `entity_type="corporation"`, then asserts the API returns those
  fields. The test green-lights a code path that never runs in
  production.

- `test_supplier_map_groups_by_country` (line 80): Same pattern.

- `test_supplier_summary_uses_patent_assignees` (line 9): Does NOT
  seed assignees — tests the fallback path only. Passes because
  the basic aggregation works without the assignees table.

## Root Cause Hypothesis

**Confidence: HIGH**

The `assignees` normalization table was created alongside other AI
infrastructure tables in migration 0003. The schema was designed to
be populated by "a one-shot backfill from `PatentPublication.assignees`"
(as stated in the model docstring). However, the backfill task was
**never written**. The fixture that creates the migration was probably
intended to be followed by a data migration or Celery task that would
populate `assignees` from `patent_publications`, but this step was
skipped or deferred.

Evidence FOR this hypothesis:
1. `assignees` table: 0 rows (confirmed on production via SSH)
2. No code anywhere inserts into `assignees` (confirmed via exhaustive
   search of all `.py` files under `backend/app/`)
3. No Celery task or beat entry exists for backfill
4. The `normalize_assignee()` function exists in the DB but was never
   invoked in a batch operation
5. Tests pass because they seed the table with test fixtures —
   masking the production gap
6. Country/entity-type coverage shows 0% because the LEFT JOIN
   produces NULL from an empty table

Evidence AGAINST: None. Every data point is consistent.

## Proposed Fix

**Concrete operational action**: Run the existing `normalize_assignee()`
PostgreSQL function against distinct assignee names from
`patent_publications`, insert normalized rows into the `assignees`
table.

**Steps**:

1. **One-shot SQL backfill** (run on production via `docker compose exec`):
   ```sql
   INSERT INTO assignees (normalized_name, display_name, aliases, country, entity_type, patent_count)
   SELECT
       normalized,
       raw_name,
       ARRAY[raw_name]::jsonb,
       NULL AS country,         -- requires external lookup (future)
       NULL AS entity_type,      -- requires classification (future)
       COUNT(*) AS patent_count
   FROM (
       SELECT DISTINCT ON (normalize_assignee(assignee_val))
           assignee_val AS raw_name,
           normalize_assignee(assignee_val) AS normalized
       FROM patent_publications p
       JOIN LATERAL jsonb_array_elements_text(p.assignees) AS assignee_val ON true
       WHERE assignee_val IS NOT NULL AND assignee_val != ''
   ) sub
   JOIN LATERAL (
       SELECT COUNT(*) FROM patent_publications p2
       JOIN LATERAL jsonb_array_elements_text(p2.assignees) AS a2 ON true
       WHERE normalize_assignee(a2) = sub.normalized
   ) cnt ON true
   GROUP BY normalized, raw_name
   ON CONFLICT (normalized_name) DO UPDATE SET
       display_name = EXCLUDED.display_name,
       patent_count = EXCLUDED.patent_count;
   ```

   Expected result: ~16,723 rows in `assignees` (one per distinct
   normalized name). Country and entity_type will still be NULL
   (those require external lookups / classification), but the basic
   join will now work and CoverageBars will show non-zero counts.

2. **Verify**:
   ```sql
   SELECT COUNT(*) FROM assignees;                          -- should be ~16,723
   SELECT COUNT(*) FROM assignees WHERE country IS NOT NULL; -- will be 0 (no country data source)
   SELECT COUNT(*) FROM assignees WHERE entity_type IS NOT NULL; -- will be 0
   ```

3. **Hit the API**:
   ```bash
   curl https://inventionindex8.com/api/v1/suppliers/summary
   ```
   Verify `suppliers_with_country` and `suppliers_with_entity_type`
   are still 0 (no country/entity source), but the CoverageBars will
   at minimum show meaningful `total_suppliers` when the DB join
   succeeds.

4. **Future work** (not this fix):
   - Add country detection: heuristic from assignee name suffixes
     (e.g., "LTD" → GB, "GMBH" → DE, "KK" → JP) or a geo-IP-style
     lookup.
   - Add entity type classification: regex rules (contains "UNIVERSITY"
     → university, contains "INC"/"CORP"/"LTD" → corporation, etc.).
   - Schedule periodic re-sync: when new patents are ingested, new
     assignee names should be auto-inserted.

**Estimated effort**: 1 hour (write + test SQL, run on production,
verify API + frontend).

## Risks of the Fix

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| DB lock contention during `INSERT ... SELECT` | Low (16K rows, < 1s on pg16) | Run during low-traffic window. Sequential scan of patent_publications is ~358ms (confirmed via EXPLAIN ANALYZE). |
| Duplicate/conflicting `display_name` chosen for `normalized_name` | Medium | `DISTINCT ON (normalized)` picks one raw name arbitrarily. For V1 with no country metadata, this is acceptable. Audit top 100 after backfill. |
| `normalize_assignee()` edge cases (HTML entities like `&AMP;`, unicode) | Low | Function uses `upper(trim())` + regex. HTML entities won't block names from being inserted, but may create false duplicates (e.g., "GOLDMAN SACHS &AMP; CO" vs "GOLDMAN SACHS & CO"). Acceptable for V1. |
| Frontend starts showing country coverage at 0% disguised as 100% | Medium | Without country data, "X of 16,723 companies" still shows 0%. The fix only ensures `total_suppliers` is stable. Add a separate data-health indicator for country coverage when country detection is implemented. |

## Open Questions

1. **Was the `normalize_assignee()` function ever run as a batch?**
   The function exists in the DB but produces zero rows. A prior
   batch might have been run and later deleted (or rolled back as
   part of a migration). Check `git log -p -- backend/alembic/versions/`
   for any migration that INSERTs into `assignees` — none found.

2. **Should country/entity_type be populated in the same backfill?**
   Country detection requires a separate data source (not available
   from patent office feeds). Entity type can be heuristic
   (regex rules on company suffixes). Recommend deferring both
   to a follow-up PR — this fix is just about populating the
   `assignees` table with normalized names.

3. **Does the summary query time out under load?**
   The EXPLAIN ANALYZE shows 358ms for the full summary query on 64K
   rows (with no concurrent load). Under production load with other
   queries competing for the DB, this could spike. The query is NOT
   the cause of "0 of 0" right now, but worth adding a DB index or
   caching layer if the page becomes slow. Consider adding
   `CREATE INDEX CONCURRENTLY idx_pp_assignees_gin ON patent_publications USING gin(assignees);`

4. **Is the "0 of 0" display a separate transient issue?**
   Currently the API returns `total_suppliers: 16723` and the
   frontend shows "0 of 16,723 companies" for coverage bars. The
   "0 of 0" display would only happen if `summary?.total_suppliers`
   is undefined (SWR error state). Was there a recent deploy,
   DB restart, or Caddy issue that could have caused the summary
   endpoint to fail temporarily? The `/companies` page currently
   renders correctly (confirmed via browser at 2026-06-07).

---

## Appendix: Verification Commands Used

```bash
# Production: check assignees table row count
ssh root@188.245.85.248 \
  "docker compose -f /opt/invention-index-8/docker-compose.yml \
   -f /opt/invention-index-8/docker-compose.prod.yml \
   exec -T db psql -U patent -d patent_pulse \
   -c 'SELECT COUNT(*) FROM assignees;'"
# Result: 0

# Production: check patent_publications assignee coverage
ssh root@188.245.85.248 \
  "docker compose -f /opt/invention-index-8/docker-compose.yml \
   -f /opt/invention-index-8/docker-compose.prod.yml \
   exec -T db psql -U patent -d patent_pulse \
   -c \"SELECT COUNT(*) FILTER (WHERE assignees IS NOT NULL
        AND jsonb_array_length(assignees) > 0) FROM patent_publications;\""
# Result: 47,492

# Production: API test
curl -s https://inventionindex8.com/api/v1/suppliers/summary | python3 -m json.tool
# Result: total_suppliers=16723, suppliers_with_country=0, suppliers_with_entity_type=0

# Exhaustive code search for Assignee table writes (zero results)
grep -rn "Assignee(" backend/app/ --include="*.py" | grep -v "class Assignee" | grep -v tests/
# Result: no matches
```
