"""
Request ID Middleware
======================

Assigns a unique UUID to every incoming request and propagates it
through the entire request lifecycle.

**Architectural Rationale:**
- Every request gets a unique identifier for end-to-end tracing.
- The ID is stored in a `contextvars.ContextVar` so all log statements
  within the request automatically include it (via the JSON formatter).
- If the client sends an `X-Request-ID` header, we honor it for
  distributed tracing across microservices.
- The ID is included in the response headers for client-side correlation.

**Connection to the system:**
- Registered as the first middleware (outermost wrapper) so all
  subsequent middleware and route handlers have access to the request ID.
- Read by `app.core.logging.context.get_request_id()`.
- Included in error responses via `app.core.exceptions.handlers`.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging.context import set_correlation_id, set_request_id

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns and propagates request and correlation IDs.

    - Generates a new `X-Request-ID` if not provided by the client.
    - Propagates `X-Correlation-ID` for distributed tracing.
    - Sets both values in contextvars for use in logging.
    - Adds both headers to the response.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request with a unique request ID."""
        # Use client-provided request ID or generate a new one
        request_id = request.headers.get(
            REQUEST_ID_HEADER,
            str(uuid.uuid4()),
        )

        # Correlation ID chains across service boundaries
        correlation_id = request.headers.get(
            CORRELATION_ID_HEADER,
            request_id,  # Default to request ID if no correlation ID
        )

        # Store in context for logging
        set_request_id(request_id)
        set_correlation_id(correlation_id)

        # Process the request
        response = await call_next(request)

        # Add IDs to response headers
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[CORRELATION_ID_HEADER] = correlation_id

        return response
