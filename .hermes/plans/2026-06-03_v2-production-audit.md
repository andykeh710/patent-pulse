# V2 Production Audit — Phase 0

> **Status:** In progress
> **Date:** 2026-06-03
> **Goal:** Stabilize production before any V2 feature work begins.

---

## 1. Production Git State

**Command:**
```bash
cd /opt/invention-index-8 && git log --oneline -5
```

**Expected:** HEAD should be at or beyond `32afc43` (latest on main)

| Check | Result |
|-------|--------|
| Production HEAD commit | ? |
| Ahead/behind main | ? |
| Uncommitted changes | ? |

---

## 2. Deploy Status

| Commit | Description | Deployed? |
|--------|-------------|-----------|
| `9a1c131` | Design overhaul (palette, skills, critique) | ? |
| `7c7341d` | Hotfix (brightness, light mode, surfaces) | ? |
| `a36d640` | PatentFiguresPanel (inline thumbnails) | ? |
| `50e9b01` | Color-token sweep + score-bar fixes | ? |
| `32afc43` | Latest | ? |

---

## 3. Container Health

**Command:**
```bash
docker compose ps
```

| Container | Status | Notes |
|-----------|--------|-------|
| frontend | ? | |
| backend | ? | |
| worker | ? | |
| beat | ? | |
| redis | ? | |
| caddy | ? | |

---

## 4. Data Completeness

### Figure Backfill
```bash
docker compose exec backend python -c "
import asyncio; from app.database import async_session_maker; from sqlalchemy import text
async def c():
    async with async_session_maker() as s:
        r = await s.execute(text('SELECT COUNT(*) FROM patent_publications WHERE figure_page_url IS NOT NULL'))
        t = await s.execute(text('SELECT COUNT(*) FROM patent_publications'))
        print(f'With figure_url: {r.scalar()} / {t.scalar()}')
asyncio.run(c())
"
```

| Metric | Count |
|--------|-------|
| Patents with figure_url | ? |
| Total patents | ? |
| Coverage % | ? |

### Company/Supplier Data
```bash
docker compose exec backend python -c "
import asyncio; from app.database import async_session_maker; from sqlalchemy import text
async def c():
    async with async_session_maker() as s:
        tables = await s.execute(text(\"SELECT tablename FROM pg_tables WHERE schemaname='public' AND (tablename LIKE '%supplier%' OR tablename LIKE '%compan%' OR tablename LIKE '%assignee%')\"))
        print('Tables:', [r[0] for r in tables])
        r = await s.execute(text('SELECT COUNT(*) FROM patent_publications WHERE assignees IS NOT NULL'))
        print(f'Patents with assignees: {r.scalar()}')
asyncio.run(c())
"
```

### Thumbnail API
```bash
curl -s "https://inventionindex8.com/api/v1/patents/US8930995/thumbnail-url" | head -200
```

---

## 5. Page-by-Page QA

| Page | Status | Issues |
|------|--------|--------|
| Landing `/` | ? | |
| Pricing `/pricing` | ? | |
| Login `/login` | ? | |
| Today `/today` | ? | |
| Patents list `/patents` | ? | |
| Patent detail `/patents/[id]` | ? | |
| Expiry `/expiry` | ? | |
| Companies `/companies` | ? | |
| Trends `/trends` | ? | |
| Search `/search` | ? | |
| Account `/account` | ? | |

---

## 6. Action Items

- [ ] Verify production git commit
- [ ] Deploy all pending commits if needed
- [ ] Complete figure backfill
- [ ] Fix Companies "0 of 0"
- [ ] Fix Expiry empty state
- [ ] Fix auth nav ("Sign in" when authenticated)
- [ ] Verify thumbnails work
- [ ] Re-run full page QA
- [ ] Confirm production healthy before Phase 1
