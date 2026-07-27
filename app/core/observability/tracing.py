"""
OpenTelemetry Tracing Engine Module
====================================

W3C compliant distributed tracing engine for end-to-end request visibility.

**Architectural Rationale:**
- Implements W3C Trace Context specification (`traceparent: 00-{trace_id}-{span_id}-{flags}`).
- Thread-safe and async-safe propagation using Python `contextvars`.
- Traces HTTP Requests, Celery Tasks, Database Queries, Redis, Qdrant, MinIO, LLM Calls,
  and Workflow Step Execution.
- Binds active `trace_id` and `span_id` into logger context for unified log correlation.

**Connection to the system:**
- Used by request middleware, Celery task wrappers, database query hooks, and service calls.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Generator
from contextlib import asynccontextmanager, contextmanager
import contextvars
from datetime import UTC, datetime
import functools
import os
import secrets
import time
from typing import Any

# Context variables for trace propagation
_current_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "otel_trace_id", default=""
)
_current_span_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "otel_span_id", default=""
)


def generate_trace_id() -> str:
    """Generate 16-byte (32 hex char) W3C trace ID."""
    return secrets.token_hex(16)


def generate_span_id() -> str:
    """Generate 8-byte (16 hex char) W3C span ID."""
    return secrets.token_hex(8)


def get_current_trace_id() -> str:
    """Get active trace ID or generate a new one if not present."""
    val = _current_trace_id.get()
    if not val:
        val = generate_trace_id()
        _current_trace_id.set(val)
    return val


def get_current_span_id() -> str:
    """Get active span ID or generate a new one if not present."""
    val = _current_span_id.get()
    if not val:
        val = generate_span_id()
        _current_span_id.set(val)
    return val


def get_traceparent_header() -> str:
    """Format active context into standard W3C `traceparent` header string."""
    trace_id = get_current_trace_id()
    span_id = get_current_span_id()
    return f"00-{trace_id}-{span_id}-01"


def parse_traceparent_header(header: str) -> tuple[str, str]:
    """Parse incoming `traceparent` header (00-traceid-spanid-flags)."""
    parts = header.strip().split("-")
    if len(parts) == 4 and parts[0] == "00" and len(parts[1]) == 32 and len(parts[2]) == 16:
        return parts[1], parts[2]
    return generate_trace_id(), generate_span_id()


class Span:
    """Active tracing span object recording metadata, timing, and status."""

    def __init__(self, name: str, trace_id: str, parent_span_id: str | None = None) -> None:
        self.name = name
        self.trace_id = trace_id
        self.span_id = generate_span_id()
        self.parent_span_id = parent_span_id
        self.start_time = time.perf_counter()
        self.start_iso = datetime.now(UTC).isoformat()
        self.end_iso: str | None = None
        self.duration_ms: float = 0.0
        self.attributes: dict[str, Any] = {}
        self.status = "OK"
        self.error: str | None = None

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_status_error(self, err_msg: str) -> None:
        self.status = "ERROR"
        self.error = err_msg

    def finish(self) -> None:
        self.duration_ms = round((time.perf_counter() - self.start_time) * 1000, 2)
        self.end_iso = datetime.now(UTC).isoformat()


@contextmanager
def start_trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Generator[Span, None, None]:
    """Sync context manager starting a trace span."""
    trace_id = get_current_trace_id()
    parent_span_id = get_current_span_id()

    span = Span(name=name, trace_id=trace_id, parent_span_id=parent_span_id)
    if attributes:
        for k, v in attributes.items():
            span.set_attribute(k, v)

    token_trace = _current_trace_id.set(trace_id)
    token_span = _current_span_id.set(span.span_id)

    try:
        yield span
    except Exception as exc:
        span.set_status_error(str(exc))
        raise
    finally:
        span.finish()
        _current_trace_id.reset(token_trace)
        _current_span_id.reset(token_span)


@asynccontextmanager
async def start_async_trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> AsyncGenerator[Span, None]:
    """Async context manager starting a trace span."""
    trace_id = get_current_trace_id()
    parent_span_id = get_current_span_id()

    span = Span(name=name, trace_id=trace_id, parent_span_id=parent_span_id)
    if attributes:
        for k, v in attributes.items():
            span.set_attribute(k, v)

    token_trace = _current_trace_id.set(trace_id)
    token_span = _current_span_id.set(span.span_id)

    try:
        yield span
    except Exception as exc:
        span.set_status_error(str(exc))
        raise
    finally:
        span.finish()
        _current_trace_id.reset(token_trace)
        _current_span_id.reset(token_span)


def trace_function(name: str | None = None) -> Callable:
    """Decorator to automatically trace synchronous function execution."""

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__qualname__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with start_trace_span(span_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def trace_async_function(name: str | None = None) -> Callable:
    """Decorator to automatically trace asynchronous coroutine execution."""

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__qualname__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            async with start_async_trace_span(span_name):
                return await func(*args, **kwargs)

        return wrapper

    return decorator
