"""
Logging Configuration Module
==============================

Configures Python's `logging` module with appropriate handlers and formatters
based on the application environment.

**Architectural Rationale:**
- Called once during application startup via `create_application()`.
- Sets up both console and file handlers.
- Production gets JSON logs; development gets colored console logs.
- Third-party library log levels are suppressed to reduce noise.
- File handler uses `RotatingFileHandler` to prevent unbounded log growth.

**Connection to the system:**
- Called by `app.main.create_application()` during startup.
- Uses formatters from `app.core.logging.formatters`.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from app.core.logging.formatters import DevelopmentFormatter, JSONFormatter


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: str = "logs/app.log",
) -> None:
    """
    Configure the application logging system.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format — "json" for production, "console" for development.
        log_file: Path to the log file for file-based logging.
    """
    # Determine the numeric log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Select formatter based on environment
    formatter: logging.Formatter
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = DevelopmentFormatter()

    # --- Root Logger ---
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear any existing handlers to prevent duplicate logs on reload
    root_logger.handlers.clear()

    # --- Console Handler ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # --- File Handler ---
    _setup_file_handler(root_logger, log_file, numeric_level, JSONFormatter())

    # --- Suppress noisy third-party loggers ---
    _configure_third_party_loggers()

    # Log startup confirmation
    logger = logging.getLogger("app.core.logging")
    logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "log_format": log_format,
            "log_file": log_file,
        },
    )


def _setup_file_handler(
    logger: logging.Logger,
    log_file: str,
    level: int,
    formatter: logging.Formatter,
) -> None:
    """
    Set up a rotating file handler.

    Args:
        logger: The logger instance to attach the handler to.
        log_file: Path to the log file.
        level: Numeric log level.
        formatter: Log formatter (always JSON for file output).
    """
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=50 * 1024 * 1024,  # 50 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def _configure_third_party_loggers() -> None:
    """
    Suppress verbose logging from third-party libraries.

    These libraries produce excessive debug output that clutters logs
    without providing value in most scenarios.
    """
    noisy_loggers = [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "aio_pika",
        "aiormq",
        "celery",
        "httpx",
        "httpcore",
        "asyncio",
        "multipart",
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger instance.

    This is the standard way to obtain a logger throughout the application.
    Always use the module's dotted path as the name for clear log provenance.

    Args:
        name: Logger name (typically ``__name__``).

    Returns:
        A configured Logger instance.

    Example::

        from app.core.logging import get_logger

        logger = get_logger(__name__)
        logger.info("Processing document", extra={"doc_id": "abc-123"})
    """
    return logging.getLogger(name)
