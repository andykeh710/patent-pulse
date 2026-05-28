"""
Tests for PR9 structured JSON logging (structlog).

Verifies that structlog emits valid JSON with required fields and that
the request-id contextvar binding works.
"""

from __future__ import annotations

import io
import json
import logging

import pytest
import structlog

from app.logging_config import configure_logging


@pytest.fixture(autouse=True)
def _reset_logging():
    """Reset structlog + stdlib logging before each test.

    Other test modules may have triggered configure_logging() via
    importing app.main, so we always start with a clean slate.
    """
    structlog.reset_defaults()
    root = logging.getLogger()
    root.handlers.clear()
    yield
    structlog.reset_defaults()
    root.handlers.clear()


def _capture_log() -> io.StringIO:
    """Call configure_logging() and redirect the handler stream to a buffer."""
    configure_logging()
    root = logging.getLogger()

    # Replace the stdout handler's stream with a StringIO so we can
    # inspect output without changing the handler/formatter chain.
    buf = io.StringIO()
    for h in root.handlers:
        if isinstance(h, logging.StreamHandler):
            h.setStream(buf)
    return buf


def test_structlog_emits_valid_json():
    """A direct structlog call produces parseable JSON with expected keys."""
    buf = _capture_log()

    log = structlog.get_logger("test_structlog")
    log.info("hello_json", user="alice")

    raw = buf.getvalue().strip()
    assert raw, "nothing written to stdout"

    record = json.loads(raw)

    assert "timestamp" in record
    assert record["level"] == "info"
    assert record["event"] == "hello_json"
    assert record["user"] == "alice"


def test_contextvar_binds_request_id():
    """Context-bound request_id appears in the JSON output."""
    buf = _capture_log()

    structlog.contextvars.bind_contextvars(request_id="abc-123")

    log = structlog.get_logger("test_context")
    log.warning("something_happened")

    structlog.contextvars.unbind_contextvars("request_id")

    raw = buf.getvalue().strip()
    record = json.loads(raw)

    assert record["request_id"] == "abc-123"
    assert record["level"] == "warning"


def test_stdlib_logging_also_produces_json():
    """Existing logging.getLogger(...).info(...) calls produce JSON."""
    buf = _capture_log()

    stdlib_logger = logging.getLogger("app.some_module")
    stdlib_logger.info("legacy_message", extra={"patent_id": "US123"})

    raw = buf.getvalue().strip()
    record = json.loads(raw)

    assert record["event"] == "legacy_message"
    assert record["level"] == "info"
    # Extra fields on stdlib log records are surfaced as top-level keys
    # via the ExtraAdder processor.
    assert record["patent_id"] == "US123"
