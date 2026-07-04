from collections.abc import AsyncGenerator
from datetime import date
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.config import Settings
from app.core import ai_models, theme_models  # noqa: F401  -- register tables
from app.core.models import Base
from app.main import app
from tests.fixtures.loader import insert_dev_fixture


def pytest_configure(config) -> None:  # noqa: D401
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "dev_fixture: load tests/fixtures/dev_50.json into the test DB session",
    )


# Note: the custom session-scoped `event_loop` fixture that used to live
# here was removed during the post-Sprint-5 audit (A1). pytest-asyncio 0.23+
# deprecated custom event_loop fixtures, and the conflict between the
# session-scoped loop and tests requesting `loop_scope="function"` was the
# root cause of ~10 spurious xfails ("event_loop fixture contention") and
# the leaked idle-in-transaction connections (A2). We now rely on
# pytest-asyncio's default per-function loop (configured via the
# `asyncio_default_fixture_loop_scope` option in pyproject.toml).


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    import os

    # Use TEST_* env vars (set in CI) to avoid colliding with the running
    # container's production DATABASE_URL / REDIS_URL.
    return Settings(
        database_url=os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://patent:secret@db:5432/patent_pulse_test",
        ),
        database_url_sync=os.environ.get(
            "TEST_DATABASE_URL_SYNC",
            "postgresql+psycopg2://patent:secret@db:5432/patent_pulse_test",
        ),
        redis_url=os.environ.get("TEST_REDIS_URL", "redis://redis:6379/1"),
        anthropic_api_key="test-key",
        uspto_api_key="test-key",
        environment="test",
        auth_secret_key="test-secret-key-for-tests",
        resend_api_key="re_test",
        email_from_address="test@example.com",
        email_dev_recipient="dev@example.com",
        email_send_mode="dev",
    )


@pytest_asyncio.fixture(scope="function")
async def db_session(test_settings: Settings) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(test_settings.database_url, echo=False)

    # Robust teardown/setup: drop the entire public schema rather than
    # iterating drop_all per-table. This avoids constraint-name drift
    # between SQLAlchemy ORM metadata and Alembic-applied migrations
    # (e.g., the fk_pp_latest_why_now_artifact_id issue).
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Seed default test users
        from app.core.ai_models import User

        session.add_all(
            [
                User(
                    id="local-user",
                    email="test@example.com",
                    display_name="Test User",
                    tier="basic",
                ),
                User(id="local-user-2", email="test2@example.com", display_name="Test User 2"),
                User(id="alert-idem-user", email="idem@example.com", display_name="Idem"),
                User(id="alert-happy-user", email="happy@example.com", display_name="Happy"),
                User(id="alert-hook-user-1", email="hook1@example.com", display_name="Hook1"),
                User(id="alert-hook-user-2", email="hook2@example.com", display_name="Hook2"),
                User(id="alert-skip-user", email="skip@example.com", display_name="Skip"),
            ]
        )
        # Seed default themes for subscription tests
        from app.core.theme_models import Theme

        session.add_all(
            [
                Theme(
                    name="AI/ML",
                    is_active=True,
                    cpc_prefixes=["G06N"],
                    keywords=["ai"],
                    assignee_keywords=["AI"],
                ),
                Theme(
                    name="Semiconductor",
                    is_active=True,
                    cpc_prefixes=["H01L"],
                    keywords=["chip"],
                    assignee_keywords=["Intel"],
                ),
                Theme(
                    name="Medical Devices",
                    is_active=True,
                    cpc_prefixes=["A61B"],
                    keywords=["implant"],
                    assignee_keywords=["Medtronic"],
                ),
            ]
        )
        await session.commit()
        yield session
        await session.rollback()

    # Symmetric teardown.
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))

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
