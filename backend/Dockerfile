FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Fix patent-client: USPTO changed API path from /dirsearch-public/ to /api/
RUN find /usr/local/lib/python3.12/site-packages/patent_client -name "api.py" \
    -path "*/public_search/*" \
    -exec sed -i 's|https://ppubs.uspto.gov/dirsearch-public|https://ppubs.uspto.gov/api|g' {} +

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
