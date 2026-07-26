"""
Log Formatters Module
======================

Custom log formatters for structured (JSON) and human-readable (console) output.

**Architectural Rationale:**
- Production uses JSON formatting for machine-parseable logs that integrate
  with log aggregation systems (ELK, Datadog, Splunk).
- Development uses colored console output for developer ergonomics.
- Both formatters include request_id from contextvars for request tracing.
- Timestamps are always UTC ISO-8601 for consistency across timezones.

**Connection to the system:**
- Used by `app.core.logging.config.setup_logging()` to configure handlers.
"""

from __future__ import annotations

import logging
import traceback
from datetime import UTC, datetime

import orjson

from app.core.logging.context import get_correlation_id, get_request_id


class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter for production environments.

    Produces one JSON object per log line with consistent schema:
    {
        "timestamp": "2024-01-15T10:30:00.000Z",
        "level": "INFO",
        "logger": "app.services.document",
        "request_id": "abc-123",
        "correlation_id": "xyz-789",
        "message": "Document processed",
        "module": "document",
        "function": "process",
        "line": 42,
        "exception": null
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string."""
        log_entry: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": get_request_id(),
            "correlation_id": get_correlation_id(),
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include exception info if present
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Include any extra fields attached to the record
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "message",
                "taskName",
            }:
                log_entry[key] = value

        # orjson for fast serialization — returns bytes, decode to str
        return orjson.dumps(log_entry, option=orjson.OPT_NON_STR_KEYS).decode("utf-8")


class DevelopmentFormatter(logging.Formatter):
    """
    Human-readable colored formatter for development environments.

    Output format:
    [2024-01-15 10:30:00] INFO     [abc-123] app.service :: Document processed
    """

    # ANSI color codes
    COLORS: dict[str, str] = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with colors for terminal output."""
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        request_id = get_request_id()

        formatted = (
            f"{self.RESET}[{timestamp}] "
            f"{color}{record.levelname:<8}{self.RESET} "
            f"[{request_id}] "
            f"{record.name} :: "
            f"{record.getMessage()}"
        )

        if record.exc_info and record.exc_info[1] is not None:
            formatted += "\n" + "".join(traceback.format_exception(*record.exc_info))

        return formatted
