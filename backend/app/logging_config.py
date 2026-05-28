"""
Structured JSON logging via structlog (PR9).

Configures structlog with JSON output to stdout. Wires stdlib logging so
existing ``logger = logging.getLogger(__name__)`` calls throughout the
codebase produce structured JSON without any code changes.

Usage:
    from app.logging_config import configure_logging
    configure_logging()

Call at startup from main.py and celery_app.py.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog with JSON output and wire stdlib logging.

    Args:
        level: Log level for the root logger (default "INFO").
    """

    # ── Timestamper shared by both pathways ────────────────────────────
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    # ── structlog pre-processors (dict → dict, wrap for formatter) ─────
    # The final processor ``wrap_for_formatter`` stores the event_dict on
    # the LogRecord so that ProcessorFormatter (on the handler) can pick
    # it up.  JSON rendering happens in the formatter for both direct
    # structlog calls AND plain stdlib logger calls.
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            timestamper,
            structlog.processors.dict_tracebacks,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # ── Wire stdlib logging into structlog ─────────────────────────────
    # ProcessorFormatter handles two code paths:
    #  1. Direct structlog:  event_dict → JSON  (uses `processors`)
    #  2. Plain stdlib:      LogRecord → dict   (uses `foreign_pre_chain`)
    #     then dict → JSON   (uses `processors`)
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.stdlib.ExtraAdder(),
            structlog.processors.add_log_level,
            timestamper,
            structlog.processors.dict_tracebacks,
        ],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Silence noisy libraries by default.
    for noisy in ("uvicorn.access", "httpx", "httpcore", "celery.worker.strategy"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
