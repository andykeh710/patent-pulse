     1|# Invention Index 8
     2|
     3|[![CI](https://github.com/andykeh710/patent-pulse/actions/workflows/ci.yml/badge.svg)](https://github.com/andykeh710/patent-pulse/actions/workflows/ci.yml)
     4|
     5|Patent intelligence system for discovering, summarizing, and analyzing patent publications.
     6|
     7|## Features
     8|
     9|- **USPTO Ingestion**: Automated weekly ingestion of new grants (Tuesday) and applications (Thursday)
    10|- **AI Summarization**: Claude-powered plain-English summaries of patent claims and mechanisms
    11|- **Interest Scoring**: Composite scoring based on CPC relevance, assignee notoriety, and claim breadth
    12|- **Expiry Watch**: Track patents approaching expiration
    13|- **Dashboard**: Visual feed of notable patents sorted by interest score
    14|
    15|## Quick Start
    16|
    17|1. **Clone and configure:**
    18|   ```bash
    19|   cp .env.example .env
    20|   # Edit .env with your API keys
    21|   ```
    22|
    23|2. **Start services:**
    24|   ```bash
    25|   make up
    26|   ```
    27|
    28|3. **Run migrations:**
    29|   ```bash
    30|   make migrate
    31|   ```
    32|
    33|4. **Access the app:**
    34|   - Frontend: http://localhost:3000
    35|   - Backend API: http://localhost:8000
    36|   - API Docs: http://localhost:8000/docs
    37|
    38|## Required API Keys
    39|
    40|- `ANTHROPIC_API_KEY`: For Claude AI summarization
    41|- `USPTO_API_KEY`: For USPTO Open Data Portal access
    42|
    43|## Development
    44|
    45|```bash
    46|# View logs
    47|make logs
    48|
    49|# Run tests
    50|make test
    51|
    52|# Shell into backend
    53|make shell
    54|
    55|# Create new migration
    56|make migration
    57|```
    58|
    59|## Architecture
    60|
    61|```
    62|┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    63|│   Frontend   │────▶│   Backend    │────▶│  PostgreSQL  │
    64|│  (Next.js)   │     │  (FastAPI)   │     │  + pgvector  │
    65|└──────────────┘     └──────────────┘     └──────────────┘
    66|                            │
    67|                            ▼
    68|                     ┌──────────────┐
    69|                     │    Redis     │
    70|                     │   (Celery)   │
    71|                     └──────────────┘
    72|                            │
    73|              ┌─────────────┼─────────────┐
    74|              ▼             ▼             ▼
    75|        ┌──────────┐  ┌──────────┐  ┌──────────┐
    76|        │  Worker  │  │   Beat   │  │  Claude  │
    77|        │ (ingest) │  │(schedule)│  │   API    │
    78|        └──────────┘  └──────────┘  └──────────┘
    79|```
    80|
    81|## Tech Stack
    82|
    83|- **Backend**: FastAPI, SQLAlchemy, Celery, Alembic
    84|- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS
    85|- **Database**: PostgreSQL 16 with pgvector
    86|- **Queue**: Redis + Celery
    87|- **AI**: Anthropic Claude API
    88|