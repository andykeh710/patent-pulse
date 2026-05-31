     1|# Invention Index 8 — Setup Guide (Portable)
     2|
     3|This guide walks through getting Invention Index 8 running on a fresh machine from the zipped
     4|distribution. The zip includes the full source tree and an optional database dump with
     5|real patent data, AI artifacts, and computed trends.
     6|
     7|---
     8|
     9|## 1. Prerequisites
    10|
    11|Install once on the target machine:
    12|
    13|- **Docker Desktop** (or Docker Engine + Docker Compose plugin v2)
    14|  - macOS: <https://www.docker.com/products/docker-desktop/>
    15|  - Linux: <https://docs.docker.com/engine/install/>
    16|- **GNU Make** (preinstalled on macOS/Linux; included with WSL on Windows)
    17|- ~5 GB free disk for images + ~1 GB for the Postgres volume (more if you re-ingest)
    18|
    19|That's it. The repo brings its own Python, Node, and Postgres via Docker.
    20|
    21|---
    22|
    23|## 2. Unpack the archive
    24|
    25|```bash
    26|unzip patent-pulse-portable.zip
    27|cd Patent-Pulse
    28|```
    29|
    30|---
    31|
    32|## 3. Configure secrets
    33|
    34|Copy the example env file and fill in your API keys:
    35|
    36|```bash
    37|cp .env.example .env
    38|```
    39|
    40|Then open `.env` and set, at minimum:
    41|
    42|| Variable | Required? | Where to get it |
    43||---|---|---|
    44|| `ANTHROPIC_API_KEY` | **Required** for any AI feature (summaries, narratives, etc.) | <https://console.anthropic.com/> |
    45|| `USPTO_API_KEY` | Required only if you plan to re-ingest fresh patents | <https://developer.uspto.gov/api-catalog> |
    46|| `EPO_OPS_CLIENT_ID` / `EPO_OPS_CLIENT_SECRET` | Optional, enables EPO ingestion and family resolution | <https://developers.epo.org/> |
    47|| `POSTGRES_PASSWORD` | Leave as `secret` for dev, or pick anything | — |
    48|
    49|If you're only running against the bundled database dump, you only need `ANTHROPIC_API_KEY`
    50|for on-demand AI features. The dump already contains pre-computed summaries, tags, scores,
    51|trends, and AI artifacts, so most of the UI works without any keys at all.
    52|
    53|---
    54|
    55|## 4. Bring up the database and Redis first
    56|
    57|```bash
    58|docker compose up -d db redis
    59|```
    60|
    61|Wait ~5 seconds for Postgres to be ready. You can verify with:
    62|
    63|```bash
    64|docker compose ps
    65|docker compose exec db pg_isready -U patent -d patent_pulse
    66|```
    67|
    68|---
    69|
    70|## 5. Restore the bundled database (recommended)
    71|
    72|The zip includes `dist/patent_pulse.dump` — a compressed pg_dump containing:
    73|
    74|- ~42,000 real patent publications (USPTO grants & applications)
    75|- ~3,000 AI artifacts (summaries, tags, Why Now, Opportunity Narratives, etc.)
    76|- ~2,400 weekly trend snapshots across CPC, tag, and assignee surfaces
    77|- ~400 patent cliff clusters and ~400 convergence signals
    78|- All migrations applied through revision 0004
    79|
    80|Restore it with:
    81|
    82|```bash
    83|# Copy the dump into the running db container
    84|docker compose cp dist/patent_pulse.dump db:/tmp/patent_pulse.dump
    85|
    86|# Restore (clean target objects first if they exist)
    87|docker compose exec -T db pg_restore \
    88|  -U patent -d patent_pulse \
    89|  --clean --if-exists --no-owner --no-acl \
    90|  /tmp/patent_pulse.dump
    91|```
    92|
    93|The restore should take 1–3 minutes. You'll see a long list of warnings about the `public`
    94|schema and the `pgvector` extension already existing — those are expected and harmless.
    95|
    96|Verify the restore:
    97|
    98|```bash
    99|docker compose exec -T db psql -U patent -d patent_pulse -c \
   100|  "SELECT count(*) AS patents FROM patent_publications;
   101|   SELECT count(*) AS artifacts FROM ai_artifacts;
   102|   SELECT count(*) AS trends FROM trend_snapshots;"
   103|```
   104|
   105|You should see ~42,258 patents, ~3,004 artifacts, ~2,414 trend rows.
   106|
   107|---
   108|
   109|## 5b. Alternative: Start from scratch (no dump)
   110|
   111|If you want to skip the dump and ingest fresh data, run only the schema migrations:
   112|
   113|```bash
   114|docker compose up -d backend
   115|docker compose exec backend alembic upgrade head
   116|```
   117|
   118|Then trigger ingestion via the `/admin/ai-runs` UI or by waiting for the weekly Celery
   119|beat schedule (see `.env.example` for cron timing).
   120|
   121|---
   122|
   123|## 6. Start everything
   124|
   125|```bash
   126|make up
   127|```
   128|
   129|This brings up `db`, `redis`, `backend`, `worker`, `beat`, and `frontend`. First boot takes
   130|~30s while Docker pulls images and installs Python/Node dependencies. Subsequent boots
   131|are fast.
   132|
   133|Watch the logs if you want:
   134|
   135|```bash
   136|make logs
   137|```
   138|
   139|---
   140|
   141|## 7. Access the app
   142|
   143|| Service | URL |
   144||---|---|
   145|| **Frontend** | <http://localhost:3000> |
   146|| **Backend API** | <http://localhost:8080> |
   147|| **API docs (Swagger)** | <http://localhost:8080/docs> |
   148|| **Health check** | <http://localhost:8080/health> |
   149|
   150|**Note on ports:** The backend container listens on port 8000 internally, but Docker
   151|Compose maps it to **8080** on the host. The README mentions 8000 in some places —
   152|that's the in-container port. Always use **8080** from your browser/curl on the host.
   153|The Next.js dev server proxies `/api/*` and `/health` from the frontend to the backend
   154|automatically (configured in `frontend/next.config.ts`).
   155|
   156|---
   157|
   158|## 8. Verify everything is working
   159|
   160|Open <http://localhost:3000> in a browser. You should see the dashboard with real
   161|patent counts. Other pages worth a smoke test:
   162|
   163|- `/trends` — should show ~461 CPC trends, top by z-score (H10W, G06T, G06F, etc.)
   164|- `/expiry` — patent cliff cards at the top + expiring patents table
   165|- `/opportunity` — tabbed opportunity feed with non-empty results
   166|- `/patents/[any-id]` — click any patent to see summary, Why Now, Opportunity Narrative
   167|
   168|Backend test suite (sanity check after restore):
   169|
   170|```bash
   171|make test
   172|```
   173|
   174|You should see **133 tests passing**.
   175|
   176|---
   177|
   178|## 9. Common operations
   179|
   180|```bash
   181|# View logs for a single service
   182|make logs-backend
   183|make logs-worker
   184|
   185|# Open a shell inside the backend container
   186|make shell
   187|
   188|# Run a fresh alembic migration after model changes
   189|make migration
   190|
   191|# Rebuild after Dockerfile or dependency changes
   192|make build
   193|
   194|# Stop everything (keeps the db volume)
   195|make down
   196|
   197|# Wipe everything including the database volume (destructive!)
   198|make clean
   199|```
   200|
   201|---
   202|
   203|## 10. Troubleshooting
   204|
   205|**"port already in use"**
   206|Something else on the host is bound to 3000, 5432, 6379, or 8080. Either stop that
   207|process or change the host port in `docker-compose.yml`.
   208|
   209|**Frontend shows "Loading..." indefinitely**
   210|Check that the backend is healthy: `curl http://localhost:8080/health`.
   211|If it returns `{"status": "degraded", "database": "..."}` the db connection is the issue —
   212|verify `make logs-db` shows the db is ready and `make logs-backend` shows no startup errors.
   213|
   214|**"connection refused" from backend to db on first boot**
   215|The backend can race the db on a cold start. Retry: `docker compose restart backend worker`.
   216|
   217|**AI features return errors**
   218|Check that `ANTHROPIC_API_KEY` is set in `.env` and the backend was restarted after
   219|editing the env file: `docker compose restart backend worker`.
   220|
   221|**Restore complains about pgvector extension**
   222|The dump references `vector` columns. If you skipped the pgvector base image
   223|(`pgvector/pgvector:pg16`) and used plain `postgres:16`, the restore will fail. The
   224|shipped `docker-compose.yml` uses the correct image — don't change it.
   225|
   226|---
   227|
   228|## 11. What's inside the zip
   229|
   230|```
   231|Patent-Pulse/
   232|├── backend/              # FastAPI + Celery app (Python 3.12 via Docker)
   233|│   ├── alembic/          # DB migrations (0001-0004)
   234|│   ├── app/              # api/, ai/, core/, ingestion/, tasks/
   235|│   ├── tests/            # 133 tests
   236|│   └── pyproject.toml
   237|├── frontend/             # Next.js 15 + React 19 app (Node 20 via Docker)
   238|│   └── src/
   239|│       ├── app/          # Routes: dashboard, trends, themes, opportunity, expiry, search, watchlist, admin
   240|│       ├── components/
   241|│       ├── hooks/
   242|│       └── lib/
   243|├── dist/
   244|│   └── patent_pulse.dump # 30 MB compressed pg_dump (42k patents + AI artifacts)
   245|├── docker-compose.yml
   246|├── Makefile
   247|├── .env.example          # Copy to .env and fill in keys
   248|├── README.md
   249|└── SETUP.md              # This file
   250|```
   251|
   252|The zip excludes: `.env`, `node_modules/`, `.next/`, `__pycache__/`, `.pytest_cache/`,
   253|`tsconfig.tsbuildinfo`, `celerybeat-schedule`, `.tmp_*.sql`, OS junk.
   254|
   255|---
   256|
   257|## 12. Cost notes
   258|
   259|The bundled database already contains pre-computed AI artifacts for many patents, so
   260|the UI is mostly free to operate. On-demand AI features (Why Now, Opportunity
   261|Narrative, etc.) hit Claude when you click the "Generate" button — each call costs a
   262|fraction of a cent at default settings (Haiku model). Batch runs through
   263|`/admin/ai-runs` show cost estimates before you commit; anything over $25 requires
   264|typing `RUN FULL BATCH` as a confirmation.
   265|