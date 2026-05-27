import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.health import router as health_router
from app.api.v1.router import v1_router
from app.config import settings
from app.database import engine

logger = logging.getLogger(__name__)

# Sprint 6: hard gate — refuse to boot in production send mode without acknowledgement.
if settings.email_send_mode == "production":
    ack = (settings.email_production_acknowledged or "").lower()
    if ack != "true":
        logger.critical(
            "EMAIL_SEND_MODE=production but EMAIL_PRODUCTION_ACKNOWLEDGED is not 'true'. "
            "Refusing to start. Set EMAIL_PRODUCTION_ACKNOWLEDGED=true in .env to acknowledge "
            "that you are sending real emails to real users via Resend."
        )
        raise SystemExit(1)

# Sprint 7: refuse to start if Stripe is in live mode (must use test keys).
if settings.stripe_api_key and settings.stripe_api_key.startswith("sk_live_"):
    logger.critical(
        "STRIPE_API_KEY starts with 'sk_live_'. Production Stripe is not allowed. "
        "Use a test key (sk_test_...) or leave STRIPE_API_KEY unset."
    )
    raise SystemExit(1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    yield
    await engine.dispose()


app = FastAPI(
    title="Patent Pulse API",
    description="Patent intelligence and summarization system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(v1_router)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal database error. The operation could not be completed."},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )


@app.get("/")
async def root() -> dict:
    return {
        "name": "Patent Pulse API",
        "version": "1.0.0",
        "docs": "/docs",
    }
