"""
Structured logging setup using structlog.

Local dev  → pretty coloured console output
Production → JSON lines (set LOG_JSON=true)

Usage anywhere in the app:
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("user.login", user_id=str(user.id), email=user.email)
"""

import logging
import sys

import structlog


def setup_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    """Configure structlog. Called once at app startup."""

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        # Production: machine-readable JSON
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: human-readable coloured output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
