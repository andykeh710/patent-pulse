# Patent Pulse

Patent intelligence system for discovering, summarizing, and analyzing patent publications.

## Features

- **USPTO Ingestion**: Automated weekly ingestion of new grants (Tuesday) and applications (Thursday)
- **AI Summarization**: Claude-powered plain-English summaries of patent claims and mechanisms
- **Interest Scoring**: Composite scoring based on CPC relevance, assignee notoriety, and claim breadth
- **Expiry Watch**: Track patents approaching expiration
- **Dashboard**: Visual feed of notable patents sorted by interest score

## Quick Start

1. **Clone and configure:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start services:**
   ```bash
   make up
   ```

3. **Run migrations:**
   ```bash
   make migrate
   ```

4. **Access the app:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Required API Keys

- `ANTHROPIC_API_KEY`: For Claude AI summarization
- `USPTO_API_KEY`: For USPTO Open Data Portal access

## Development

```bash
# View logs
make logs

# Run tests
make test

# Shell into backend
make shell

# Create new migration
make migration
```

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│  PostgreSQL  │
│  (Next.js)   │     │  (FastAPI)   │     │  + pgvector  │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │    Redis     │
                     │   (Celery)   │
                     └──────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Worker  │  │   Beat   │  │  Claude  │
        │ (ingest) │  │(schedule)│  │   API    │
        └──────────┘  └──────────┘  └──────────┘
```

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Celery, Alembic
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS
- **Database**: PostgreSQL 16 with pgvector
- **Queue**: Redis + Celery
- **AI**: Anthropic Claude API
