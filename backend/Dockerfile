# ── Builder stage: install poetry, export deps to /build/deps ──────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==1.8.*

COPY pyproject.toml poetry.lock ./

RUN poetry lock --no-update \
    && poetry export --without-hashes -f requirements.txt -o requirements.txt \
    && pip install --no-cache-dir --target=/build/deps -r requirements.txt


# ── Runtime stage: system libs + copy deps from builder + app code ────
FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/deps /usr/local/lib/python3.12/site-packages
COPY --from=builder /build/deps/bin /usr/local/bin

COPY . .

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
# Fix patent_client for pydantic-settings v2 (SETTINGS.DEFAULT removed)
RUN sed -i 's/SETTINGS\.DEFAULT\.BASE_DIR = str(BASE_DIR)/# patched for pydantic-settings v2/' /usr/local/lib/python3.12/site-packages/patent_client/__init__.py
# Pre-create patent_client cache dirs (avoids PermissionError in non-root containers)
RUN mkdir -p /home/appuser/.patent_client && chown -R appuser:appuser /home/appuser
RUN mkdir -p /usr/local/lib/python3.12/_build && chown appuser:appuser /usr/local/lib/python3.12/_build
ENV PATENT_CLIENT_BASE_DIR=/home/appuser/.patent_client
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
