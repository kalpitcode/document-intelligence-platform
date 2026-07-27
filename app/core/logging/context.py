"""
Logging Context Module
=======================

Provides request-scoped and operation-scoped context using Python's `contextvars`.

**Architectural Rationale:**
- `contextvars` gives us thread-safe, async-safe request-scoped state.
- Automatically tracks `request_id`, `trace_id`, `user_id`, `workflow_id`, `document_id`,
  `session_id`, `service`, `operation`, `duration_ms`, and `error_code`.
- Read by `JSONFormatter` to include all structured observability keys in every log record.

**Connection to the system:**
- Set by request middleware, service wrappers, and tasks.
- Read by `app.core.logging.formatters.JSONFormatter`.
"""

from __future__ import annotations

import contextvars

_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="no-request-id")
_correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="no-correlation-id")
_user_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)
_workflow_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("workflow_id", default=None)
_document_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("document_id", default=None)
_session_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("session_id", default=None)
_service_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("service", default="dip-platform")
_operation_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("operation", default=None)
_duration_ms_ctx: contextvars.ContextVar[float | None] = contextvars.ContextVar("duration_ms", default=None)
_error_code_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("error_code", default=None)


def get_request_id() -> str:
    return _request_id_ctx.get()

def set_request_id(request_id: str) -> contextvars.Token[str]:
    return _request_id_ctx.set(request_id)

def get_correlation_id() -> str:
    return _correlation_id_ctx.get()

def set_correlation_id(correlation_id: str) -> contextvars.Token[str]:
    return _correlation_id_ctx.set(correlation_id)

def get_user_id() -> str | None:
    return _user_id_ctx.get()

def set_user_id(user_id: str | None) -> contextvars.Token[str | None]:
    return _user_id_ctx.set(user_id)

def get_workflow_id() -> str | None:
    return _workflow_id_ctx.get()

def set_workflow_id(workflow_id: str | None) -> contextvars.Token[str | None]:
    return _workflow_id_ctx.set(workflow_id)

def get_document_id() -> str | None:
    return _document_id_ctx.get()

def set_document_id(document_id: str | None) -> contextvars.Token[str | None]:
    return _document_id_ctx.set(document_id)

def get_session_id() -> str | None:
    return _session_id_ctx.get()

def set_session_id(session_id: str | None) -> contextvars.Token[str | None]:
    return _session_id_ctx.set(session_id)

def get_service() -> str:
    return _service_ctx.get()

def set_service(service: str) -> contextvars.Token[str]:
    return _service_ctx.set(service)

def get_operation() -> str | None:
    return _operation_ctx.get()

def set_operation(operation: str | None) -> contextvars.Token[str | None]:
    return _operation_ctx.set(operation)

def get_duration_ms() -> float | None:
    return _duration_ms_ctx.get()

def set_duration_ms(duration_ms: float | None) -> contextvars.Token[float | None]:
    return _duration_ms_ctx.set(duration_ms)

def get_error_code() -> str | None:
    return _error_code_ctx.get()

def set_error_code(error_code: str | None) -> contextvars.Token[str | None]:
    return _error_code_ctx.set(error_code)
