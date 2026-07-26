"""
Logging Package
================

Enterprise-grade structured logging for the Document Intelligence Platform.

Provides:
- `setup_logging()` — One-time configuration during application startup.
- `get_logger()` — Factory function for obtaining named loggers.

Usage::

    from app.core.logging import get_logger, setup_logging

    # During startup
    setup_logging(log_level="INFO", log_format="json")

    # In any module
    logger = get_logger(__name__)
    logger.info("Request processed", extra={"duration_ms": 42})
"""

from __future__ import annotations

from app.core.logging.config import get_logger, setup_logging
from app.core.logging.context import (
    get_correlation_id,
    get_request_id,
    set_correlation_id,
    set_request_id,
)

__all__ = [
    "get_logger",
    "get_correlation_id",
    "get_request_id",
    "set_correlation_id",
    "set_request_id",
    "setup_logging",
]
