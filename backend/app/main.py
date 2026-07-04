import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.health import router as health_router
from app.api.v1.router import v1_router
from app.api.v1.share import (
    robots_txt as _robots_endpoint,
)
from app.api.v1.share import (
    sitemap_companies as _sitemap_companies,
)
from app.api.v1.share import (
    sitemap_index as _sitemap_endpoint,
)
from app.api.v1.share import (
    sitemap_pages as _sitemap_pages,
)
from app.api.v1.share import (
    sitemap_patents as _sitemap_patents,
)
from app.api.v1.share import (
    sitemap_themes as _sitemap_themes,
)
from app.api.v1.webhooks import public_router
from app.config import settings
from app.database import engine
from app.logging_config import configure_logging
from app.middleware.rate_limit import limiter
from app.middleware.request_id import RequestIDMiddleware
from app.observability.sentry import init_sentry

# Structured JSON logging — call before any logger.info / logger.critical.
configure_logging()

# Sentry — call before FastAPI() instance so startup errors are captured.
init_sentry()

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

# Phase 4: Stripe live-mode safety gate — refuse to start in prod unless acknowledged.
if settings.stripe_mode == "live":
    ack = (settings.stripe_live_acknowledged or "").lower()
    if ack != "true":
        logger.critical(
            "STRIPE_MODE=live but STRIPE_LIVE_ACKNOWLEDGED is not 'true'. "
            "Refusing to start. Set STRIPE_LIVE_ACKNOWLEDGED=true in .env to acknowledge "
            "that you are processing real payments in Stripe LIVE mode."
        )
        raise SystemExit(1)
    # Additional sanity: if STRIPE_MODE=live but the key still looks like test, warn loudly.
    if settings.stripe_api_key and not settings.stripe_api_key.startswith("sk_live_"):
        logger.critical(
            "STRIPE_MODE=live but STRIPE_API_KEY does not start with 'sk_live_'. "
            "Refusing to start. Ensure you are using live-mode Stripe keys."
        )
        raise SystemExit(1)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    # Phase 6: seed blog posts from content/blog/*.md
    try:
        from app.api.v1.blog import seed_blog_posts

        count = await seed_blog_posts()
        if count:
            logger.info("Seeded %d blog posts from content/blog/", count)
    except Exception:
        logger.warning("Blog seed failed (non-fatal)")
    yield
    await engine.dispose()


app = FastAPI(
    title="Invention Index 8 API",
    description="Invention intelligence and opportunity indexing system",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiter — must be on app.state before SlowAPIMiddleware.
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request-ID middleware — binds a UUID to structlog context per request.
app.add_middleware(RequestIDMiddleware)

# Rate-limit middleware — applies default_limits globally.
app.add_middleware(SlowAPIMiddleware)

app.include_router(health_router)
app.include_router(v1_router)
app.include_router(public_router)

# Public routes (not under /api/v1)
app.get("/sitemap.xml")(_sitemap_endpoint)
app.get("/sitemap-companies.xml")(_sitemap_companies)
app.get("/sitemap-themes.xml")(_sitemap_themes)
app.get("/sitemap-patents.xml")(_sitemap_patents)
app.get("/sitemap-pages.xml")(_sitemap_pages)
app.get("/robots.txt")(_robots_endpoint)


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
        "name": "Invention Index 8 API",
        "version": "1.0.0",
        "docs": "/docs",
    }
