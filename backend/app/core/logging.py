"""
Structured logging configuration using structlog.

All application code should use get_logger() to obtain a logger instance.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import get_settings


# Loggers that are too verbose at INFO — clamp them to WARNING
_NOISY_LOGGERS = [
    "asyncssh",        # SSH channel open/close/command spam
    "asyncio",         # low-level event-loop internals
    "uvicorn.access",  # per-request HTTP lines (already printed by uvicorn)
    "botocore",        # AWS SDK wire-level details
    "boto3",
    "urllib3",
    "httpcore",
    "httpx",
]


def configure_logging() -> None:
    """
    Configure structlog and standard-library logging.

    Call this once during application startup.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level, logging.INFO)

    # Silence noisy third-party loggers regardless of root level
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Always use clean human-readable console output (not JSON blobs)
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=False),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """
    Return a structlog logger bound to the given name.

    Usage::

        logger = get_logger(__name__)
        logger.info("metric_ingested", hostname="ec2-host", cpu=92.4)
    """
    return structlog.get_logger(name)
