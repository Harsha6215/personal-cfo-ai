"""
Structured JSON logging setup using structlog.
Every request gets logged with method, path, status, and duration.
"""

import logging
import sys

import structlog


def setup_logging() -> None:
    """Configure structlog for structured JSON output."""

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if True  # swap to JSONRenderer() in production
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
