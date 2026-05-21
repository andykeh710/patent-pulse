# Patent Pulse — Setup Guide (Portable)

This guide walks through getting Patent Pulse running on a fresh machine from the zipped
distribution. The zip includes the full source tree and an optional database dump with
real patent data, AI artifacts, and computed trends.

---

## 1. Prerequisites

Install once on the target machine:

- **Docker Desktop** (or Docker Engine + Docker Compose plugin v2)
  - macOS: <https://www.docker.com/products/docker-desktop/>
  - Linux: <https://docs.docker.com/engine/install/>
- **GNU Make** (preinstalled on macOS/Linux; included with WSL on Windows)
- ~5 GB free disk for images + ~1 GB for the Postgres volume (more if you re-ingest)

That's it. The repo brings its own Python, Node, and Postgres via Docker.

---

## 2. Unpack the archive

```bash
unzip patent-pulse-portable.zip
cd Patent-Pulse
```

---

## 3. Configure secrets

Copy the example env file and fill in your API keys:

```bash
cp .env.example .env
```

Then open `.env` and set, at minimum:

| Variable | Required? | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Required** for any AI feature (summaries, narratives, etc.) | <https://console.anthropic.com/> |
| `USPTO_API_KEY` | Required only if you plan to re-ingest fresh patents | <https://developer.uspto.gov/api-catalog> |
| `EPO_OPS_CLIENT_ID` / `EPO_OPS_CLIENT_SECRET` | Optional, enables EPO ingestion and family resolution | <https://developers.epo.org/> |
| `POSTGRES_PASSWORD` | Leave as `secret` for dev, or pick anything | — |

If you're only running against the bundled database dump, you only need `ANTHROPIC_API_KEY`
for on-demand AI features. The dump already contains pre-computed summaries, tags, scores,
trends, and AI artifacts, so most of the UI works without any keys at all.

---

## 4. Bring up the database and Redis first

```bash
docker compose up -d db redis
```

Wait ~5 seconds for Postgres to be ready. You can verify with:

```bash
docker compose ps
docker compose exec db pg_isready -U patent -d patent_pulse
```

---

## 5. Restore the bundled database (recommended)

The zip includes `dist/patent_pulse.dump` — a compressed pg_dump containing:

- ~42,000 real patent publications (USPTO grants & applications)
- ~3,000 AI artifacts (summaries, tags, Why Now, Opportunity Narratives, etc.)
- ~2,400 weekly trend snapshots across CPC, tag, and assignee surfaces
- ~400 patent cliff clusters and ~400 convergence signals
- All migrations applied through revision 0004

Restore it with:

```bash
# Copy the dump into the running db container
docker compose cp dist/patent_pulse.dump db:/tmp/patent_pulse.dump

# Restore (clean target objects first if they exist)
docker compose exec -T db pg_restore \
  -U patent -d patent_pulse \
  --clean --if-exists --no-owner --no-acl \
  /tmp/patent_pulse.dump
```

The restore should take 1–3 minutes. You'll see a long list of warnings about the `public`
schema and the `pgvector` extension already existing — those are expected and harmless.

Verify the restore:

```bash
docker compose exec -T db psql -U patent -d patent_pulse -c \
  "SELECT count(*) AS patents FROM patent_publications;
   SELECT count(*) AS artifacts FROM ai_artifacts;
   SELECT count(*) AS trends FROM trend_snapshots;"
```

You should see ~42,258 patents, ~3,004 artifacts, ~2,414 trend rows.

---

## 5b. Alternative: Start from scratch (no dump)

If you want to skip the dump and ingest fresh data, run only the schema migrations:

```bash
docker compose up -d backend
docker compose exec backend alembic upgrade head
```

Then trigger ingestion via the `/admin/ai-runs` UI or by waiting for the weekly Celery
beat schedule (see `.env.example` for cron timing).

---

## 6. Start everything

```bash
make up
```

This brings up `db`, `redis`, `backend`, `worker`, `beat`, and `frontend`. First boot takes
~30s while Docker pulls images and installs Python/Node dependencies. Subsequent boots
are fast.

Watch the logs if you want:

```bash
make logs
```

---

## 7. Access the app

| Service | URL |
|---|---|
| **Frontend** | <http://localhost:3000> |
| **Backend API** | <http://localhost:8080> |
| **API docs (Swagger)** | <http://localhost:8080/docs> |
| **Health check** | <http://localhost:8080/health> |

**Note on ports:** The backend container listens on port 8000 internally, but Docker
Compose maps it to **8080** on the host. The README mentions 8000 in some places —
that's the in-container port. Always use **8080** from your browser/curl on the host.
The Next.js dev server proxies `/api/*` and `/health` from the frontend to the backend
automatically (configured in `frontend/next.config.ts`).

---

## 8. Verify everything is working

Open <http://localhost:3000> in a browser. You should see the dashboard with real
patent counts. Other pages worth a smoke test:

- `/trends` — should show ~461 CPC trends, top by z-score (H10W, G06T, G06F, etc.)
- `/expiry` — patent cliff cards at the top + expiring patents table
- `/opportunity` — tabbed opportunity feed with non-empty results
- `/patents/[any-id]` — click any patent to see summary, Why Now, Opportunity Narrative

Backend test suite (sanity check after restore):

```bash
make test
```

You should see **133 tests passing**.

---

## 9. Common operations

```bash
# View logs for a single service
make logs-backend
make logs-worker

# Open a shell inside the backend container
make shell

# Run a fresh alembic migration after model changes
make migration

# Rebuild after Dockerfile or dependency changes
make build

# Stop everything (keeps the db volume)
make down

# Wipe everything including the database volume (destructive!)
make clean
```

---

## 10. Troubleshooting

**"port already in use"**
Something else on the host is bound to 3000, 5432, 6379, or 8080. Either stop that
process or change the host port in `docker-compose.yml`.

**Frontend shows "Loading..." indefinitely**
Check that the backend is healthy: `curl http://localhost:8080/health`.
If it returns `{"status": "degraded", "database": "..."}` the db connection is the issue —
verify `make logs-db` shows the db is ready and `make logs-backend` shows no startup errors.

**"connection refused" from backend to db on first boot**
The backend can race the db on a cold start. Retry: `docker compose restart backend worker`.

**AI features return errors**
Check that `ANTHROPIC_API_KEY` is set in `.env` and the backend was restarted after
editing the env file: `docker compose restart backend worker`.

**Restore complains about pgvector extension**
The dump references `vector` columns. If you skipped the pgvector base image
(`pgvector/pgvector:pg16`) and used plain `postgres:16`, the restore will fail. The
shipped `docker-compose.yml` uses the correct image — don't change it.

---

## 11. What's inside the zip

```
Patent-Pulse/
├── backend/              # FastAPI + Celery app (Python 3.12 via Docker)
│   ├── alembic/          # DB migrations (0001-0004)
│   ├── app/              # api/, ai/, core/, ingestion/, tasks/
│   ├── tests/            # 133 tests
│   └── pyproject.toml
├── frontend/             # Next.js 15 + React 19 app (Node 20 via Docker)
│   └── src/
│       ├── app/          # Routes: dashboard, trends, themes, opportunity, expiry, search, watchlist, admin
│       ├── components/
│       ├── hooks/
│       └── lib/
├── dist/
│   └── patent_pulse.dump # 30 MB compressed pg_dump (42k patents + AI artifacts)
├── docker-compose.yml
├── Makefile
├── .env.example          # Copy to .env and fill in keys
├── README.md
└── SETUP.md              # This file
```

The zip excludes: `.env`, `node_modules/`, `.next/`, `__pycache__/`, `.pytest_cache/`,
`tsconfig.tsbuildinfo`, `celerybeat-schedule`, `.tmp_*.sql`, OS junk.

---

## 12. Cost notes

The bundled database already contains pre-computed AI artifacts for many patents, so
the UI is mostly free to operate. On-demand AI features (Why Now, Opportunity
Narrative, etc.) hit Claude when you click the "Generate" button — each call costs a
fraction of a cent at default settings (Haiku model). Batch runs through
`/admin/ai-runs` show cost estimates before you commit; anything over $25 requires
typing `RUN FULL BATCH` as a confirmation.
