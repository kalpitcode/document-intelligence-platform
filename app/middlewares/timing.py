"""
Processing Time Middleware
===========================

Adds an `X-Process-Time` header to every response.

**Architectural Rationale:**
- Provides client-visible latency information without requiring
  access to server logs.
- Useful for debugging slow requests from the client side.
- Lightweight — uses `time.perf_counter()` for nanosecond precision
  without measurable overhead.

**Connection to the system:**
- Registered in the middleware stack via `app.middlewares.register_middleware()`.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class ProcessingTimeMiddleware(BaseHTTPMiddleware):
    """
    Middleware that measures request processing time and adds it
    as a response header.

    Header: `X-Process-Time` (value in seconds with microsecond precision)
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Measure and report processing time."""
        start_time = time.perf_counter()

        response = await call_next(request)

        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.6f}"

        return response
