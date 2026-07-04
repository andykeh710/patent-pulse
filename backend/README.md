# Patent-Pulse Backend

FastAPI application for the Invention Index 8 patent intelligence platform.

## Local Development Setup

**Requires Python 3.12.** Check with `python3 --version`.

```bash
# 1. Create virtual environment
python3 -m venv .venv

# 2. Activate it
source .venv/bin/activate

# 3. Install dependencies
pip install poetry
poetry install --no-root

# 4. Verify
python -m pytest --collect-only -q | tail -3
```

If the venv is broken (wrong Python version, missing pip/pytest):

```bash
python3 -m venv --clear .venv
source .venv/bin/activate
pip install poetry
poetry install --no-root
```

## Dependency Management

Poetry is the canonical dependency authority for this project.
`requirements.txt` and `requirements-dev.txt` are **generated exports**
consumed by Docker builds. Never edit them by hand.

```bash
# After changing pyproject.toml:
poetry lock                          # resolve + update lock
make deps-export                     # regenerate requirements*.txt
```

CI enforces staleness via `make deps-check` — if requirements files
drift from poetry.lock, the build fails.

## Running Tests

```bash
# Inside Docker (recommended — matches CI environment):
docker compose exec backend pytest

# Locally (requires running PostgreSQL + Redis):
TEST_DATABASE_URL=postgresql+asyncpg://patent:secret@localhost:5432/patent_pulse_test \
TEST_DATABASE_URL_SYNC=postgresql+psycopg2://patent:secret@localhost:5432/patent_pulse_test \
TEST_REDIS_URL=redis://localhost:6379/1 \
python -m pytest
```

## Docker Build Targets

| Target | What it includes | When to use |
|---|---|---|
| `prod` (default) | Runtime deps only | Production, CI staging |
| `dev` | Runtime + pytest, ruff, coverage | Local development |

The `docker-compose.override.yml` automatically selects the `dev` target
for local work.
