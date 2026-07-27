"""
Log Formatters Module
======================

Custom log formatters for structured (JSON) and human-readable (console) output.

**Architectural Rationale:**
- Production uses JSON formatting for machine-parseable logs that integrate
  with log aggregation systems (ELK, Datadog, Splunk).
- Includes all Milestone 9 required observability context keys: `timestamp`, `level`,
  `request_id`, `trace_id`, `user_id`, `workflow_id`, `document_id`, `session_id`,
  `service`, `operation`, `duration_ms`, `error_code`.
- Implements strict secret redacting to prevent accidental logging of credentials or raw document payloads.
"""

from __future__ import annotations

import logging
import re
import traceback
from datetime import UTC, datetime
from typing import Any

import orjson

from app.core.logging.context import (
    get_correlation_id,
    get_document_id,
    get_duration_ms,
    get_error_code,
    get_operation,
    get_request_id,
    get_service,
    get_session_id,
    get_user_id,
    get_workflow_id,
)
from app.core.observability.tracing import get_current_trace_id

SENSITIVE_KEYS = {
    "password",
    "token",
    "secret",
    "authorization",
    "api_key",
    "apikey",
    "credentials",
    "private_key",
    "access_token",
    "refresh_token",
}


def redact_sensitive_data(data: Any) -> Any:
    """Recursively mask sensitive keys in dict structures."""
    if isinstance(data, dict):
        cleaned: dict[str, Any] = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                cleaned[k] = "******[REDACTED]******"
            else:
                cleaned[k] = redact_sensitive_data(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    elif isinstance(data, str):
        # Mask authorization headers if stringified
        if re.search(r"(bearer|basic)\s+[a-zA-Z0-9\._\-]+", data, re.IGNORECASE):
            return re.sub(r"(bearer|basic)\s+[a-zA-Z0-9\._\-]+", r"\1 ******[REDACTED]******", data, flags=re.IGNORECASE)
    return data


class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter producing strictly schema-compliant observability output.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record into structured JSON."""
        # Extract explicit extra properties or record fields
        record_dict = getattr(record, "__dict__", {})

        user_id = record_dict.get("user_id") or get_user_id()
        workflow_id = record_dict.get("workflow_id") or get_workflow_id()
        document_id = record_dict.get("document_id") or get_document_id()
        session_id = record_dict.get("session_id") or get_session_id()
        service = record_dict.get("service") or get_service()
        operation = record_dict.get("operation") or get_operation() or record.funcName
        duration_ms = record_dict.get("duration_ms") or get_duration_ms()
        error_code = record_dict.get("error_code") or get_error_code()

        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": get_request_id(),
            "correlation_id": get_correlation_id(),
            "trace_id": get_current_trace_id(),
            "user_id": str(user_id) if user_id else None,
            "workflow_id": str(workflow_id) if workflow_id else None,
            "document_id": str(document_id) if document_id else None,
            "session_id": str(session_id) if session_id else None,
            "service": service,
            "operation": operation,
            "duration_ms": duration_ms,
            "error_code": error_code,
            "message": redact_sensitive_data(record.getMessage()),
            "module": record.module,
            "line": record.lineno,
        }

        # Include exception info if present
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": redact_sensitive_data(str(record.exc_info[1])),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Include extra payload parameters safely
        for key, value in record_dict.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName", "levelname",
                "levelno", "lineno", "module", "msecs", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread", "threadName",
                "exc_info", "exc_text", "message", "taskName", "user_id", "workflow_id",
                "document_id", "session_id", "service", "operation", "duration_ms", "error_code"
            }:
                log_entry[key] = redact_sensitive_data(value)

        return orjson.dumps(log_entry, option=orjson.OPT_NON_STR_KEYS).decode("utf-8")


class DevelopmentFormatter(logging.Formatter):
    """Human-readable colored formatter for local terminal development."""

    COLORS: dict[str, str] = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[41m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        req_id = get_request_id()
        trace_id = get_current_trace_id()

        formatted = (
            f"{self.RESET}[{timestamp}] "
            f"{color}{record.levelname:<8}{self.RESET} "
            f"[{req_id} | trace:{trace_id[:8]}] "
            f"{record.name} :: "
            f"{redact_sensitive_data(record.getMessage())}"
        )

        if record.exc_info and record.exc_info[1] is not None:
            formatted += "\n" + "".join(traceback.format_exception(*record.exc_info))

        return formatted
