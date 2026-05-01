import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import date
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.config import Settings
from app.core.models import Base
from app.core import ai_models, theme_models  # noqa: F401  -- register tables
from app.main import app
from tests.fixtures.loader import insert_dev_fixture


def pytest_configure(config) -> None:  # noqa: D401
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "dev_fixture: load tests/fixtures/dev_50.json into the test DB session",
    )


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://patent:secret@db:5432/patent_pulse_test",
        database_url_sync="postgresql+psycopg2://patent:secret@db:5432/patent_pulse_test",
        redis_url="redis://redis:6379/1",
        anthropic_api_key="test-key",
        uspto_api_key="test-key",
        environment="test",
    )


@pytest_asyncio.fixture(scope="function")
async def db_session(test_settings: Settings) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(test_settings.database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_patent_data() -> dict[str, Any]:
    return {
        "doc_id": "USPTO:12345678",
        "office": "USPTO",
        "publication_number": "12345678",
        "application_number": "17/123456",
        "kind_code": "B2",
        "filing_date": date(2022, 1, 15),
        "grant_date": date(2024, 3, 15),
        "assignees": ["Acme Corporation"],
        "inventors": ["John Doe", "Jane Smith"],
        "cpc": ["G06F 21/00", "H04L 9/32"],
        "ipc": ["G06F 21/00"],
        "title": "System and Method for Secure Authentication",
        "abstract": "A system for authenticating users using biometric data...",
        "claims_text": "1. A method for authenticating a user comprising...",
        "legal_status": "GRANTED",
        "estimated_expiry_date": date(2042, 1, 15),
    }


@pytest_asyncio.fixture
async def dev_fixture(db_session: AsyncSession) -> int:
    """Load the deterministic 50-patent dev fixture into the active session.

    Use via ``@pytest.mark.dev_fixture`` + a ``dev_fixture`` argument:

        @pytest.mark.dev_fixture
        async def test_something(dev_fixture, client):
            assert dev_fixture >= 0
    """
    return await insert_dev_fixture(db_session)


@pytest.fixture
def sample_uspto_raw_grant() -> dict[str, Any]:
    return {
        "patent_number": "12345678",
        "application_number": "17/123456",
        "kind_code": "B2",
        "filing_date": "2022-01-15",
        "issue_date": "2024-03-15",
        "invention_title": "System and Method for Secure Authentication",
        "abstract_text": "A system for authenticating users using biometric data...",
        "claims": "1. A method for authenticating a user comprising...",
        "assignees": [{"assignee_name": "Acme Corporation"}],
        "inventors": [{"inventor_name": "John Doe"}, {"inventor_name": "Jane Smith"}],
        "cpc_codes": [{"code": "G06F 21/00"}, {"code": "H04L 9/32"}],
        "ipc_codes": [{"code": "G06F 21/00"}],
    }
