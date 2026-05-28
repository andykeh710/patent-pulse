"""
Request-ID middleware (PR9).

Generates a UUID v4 per request, binds it to structlog's context so every
log line emitted during the request carries the request_id, and sets an
``X-Request-ID`` response header for client correlation.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that attaches a unique ``request_id`` to every request.

    The ID is bound to structlog context so downstream log calls
    automatically include it.  It is also returned in the
    ``X-Request-ID`` response header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())

        # Bind to structlog context — all log calls during this request
        # will include {"request_id": "..."}.
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        # Unbind so the context doesn't leak to the next request.
        structlog.contextvars.unbind_contextvars("request_id")

        return response
