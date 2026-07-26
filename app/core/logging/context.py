"""
Logging Context Module
=======================

Provides request-scoped context using Python's `contextvars`.

**Architectural Rationale:**
- `contextvars` gives us thread-safe, async-safe request-scoped state.
- The request ID is set once by the Request ID middleware and automatically
  flows through all layers (services, repositories, utilities) without
  being passed explicitly as a function argument.
- The JSON formatter reads this context to include request_id in every log line.

**Connection to the system:**
- Set by `app.middlewares.request_id.RequestIDMiddleware`
- Read by `app.core.logging.formatters.JSONFormatter`
"""

from __future__ import annotations

import contextvars

# Context variable for the current request ID.
# Default is "no-request-id" for logs emitted outside a request context
# (e.g., during application startup).
_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id",
    default="no-request-id",
)

# Context variable for the current correlation ID (for distributed tracing).
_correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id",
    default="no-correlation-id",
)


def get_request_id() -> str:
    """Get the current request ID from context."""
    return _request_id_ctx.get()


def set_request_id(request_id: str) -> contextvars.Token[str]:
    """
    Set the request ID in the current context.

    Returns:
        Token that can be used to reset the context variable.
    """
    return _request_id_ctx.set(request_id)


def get_correlation_id() -> str:
    """Get the current correlation ID from context."""
    return _correlation_id_ctx.get()


def set_correlation_id(correlation_id: str) -> contextvars.Token[str]:
    """
    Set the correlation ID in the current context.

    Returns:
        Token that can be used to reset the context variable.
    """
    return _correlation_id_ctx.set(correlation_id)
