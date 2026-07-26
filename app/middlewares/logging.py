"""
Logging Middleware
==================

Logs structured information about every HTTP request and response.

**Architectural Rationale:**
- Provides a centralized audit trail of all API activity.
- Logs method, path, status code, and duration for every request.
- Uses structured logging (extra fields) for machine-parseable output.
- Excludes health check endpoints from verbose logging to reduce noise
  in production (health checks fire every few seconds from load balancers).

**Connection to the system:**
- Registered after `RequestIDMiddleware` so request_id is available.
- Uses `app.core.logging.get_logger()` for consistent log output.
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.middlewares.access")

# Endpoints to exclude from access logging (too noisy in production)
_EXCLUDED_PATHS: set[str] = {
    "/api/v1/health/live",
    "/api/v1/health/ready",
    "/health",
    "/metrics",
}


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs HTTP request and response metadata.

    Log output includes:
    - HTTP method and path
    - Response status code
    - Request processing duration (milliseconds)
    - Client IP address
    - User-Agent header
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Log request/response information."""
        # Skip logging for excluded paths
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Determine log level based on status code
        status_code = response.status_code
        if status_code >= 500:
            log_level = logging.ERROR
        elif status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        logger.log(
            log_level,
            "%s %s %d %.2fms",
            request.method,
            request.url.path,
            status_code,
            duration_ms,
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "query_params": str(request.query_params) if request.query_params else None,
            },
        )

        return response
