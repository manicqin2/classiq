"""
Structured logging configuration using structlog.

Provides JSON-formatted logs for production and colored logs for development.
"""

import logging
import sys

import structlog

from src.common.config import settings


def configure_logging():
    """Configure structured logging with environment-specific output format."""

    # Determine output format based on environment
    if settings.environment == "development":
        # Colored console output for development
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        # JSON output for production
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )


# Initialize logging on module import
configure_logging()

# Export logger factory
get_logger = structlog.get_logger
