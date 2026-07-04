import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# Celery prefork workers fork after import; each asyncio.run() call needs a fresh
# connection not tied to the parent's event loop, so use NullPool in workers.
_in_celery_worker = os.environ.get("CELERY_WORKER", "") == "true"

_engine_kwargs: dict = {
    "echo": settings.environment == "development",
    "pool_pre_ping": True,
    # Post-Sprint-5 audit (A2): asyncpg connections opened inside asyncio.run()
    # loops in Celery tasks can leak into idle-in-transaction state when the
    # loop tears down before the connection is fully released. Set a
    # server-side idle-in-transaction timeout so Postgres reaps them within
    # 60s instead of accumulating indefinitely.
    "connect_args": {
        "server_settings": {
            "idle_in_transaction_session_timeout": "60000",  # ms = 60 sec
            "application_name": "patent_pulse_worker" if _in_celery_worker else "patent_pulse_app",
        },
    },
}
if _in_celery_worker:
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_async_engine(settings.database_url, **_engine_kwargs)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
