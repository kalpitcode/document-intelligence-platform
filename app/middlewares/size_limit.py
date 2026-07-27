"""
Request Size Limit Middleware Module
======================================

Enforces maximum HTTP request payload size caps (50MB) to protect system resources.

**Architectural Rationale:**
- Rejects oversized requests exceeding `MAX_REQUEST_SIZE_BYTES` with HTTP 413 Payload Too Large.
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware checking request payload size caps."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        content_length = request.headers.get("content-length")

        if content_length and content_length.isdigit():
            length_bytes = int(content_length)
            if length_bytes > settings.max_request_size_bytes:
                logger.warning(
                    "Request size limit exceeded",
                    extra={
                        "size_bytes": length_bytes,
                        "max_bytes": settings.max_request_size_bytes,
                        "path": request.url.path,
                    },
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "status_code": 413,
                        "message": "Request payload exceeds maximum allowed size (50MB limit).",
                        "details": {
                            "content_length_bytes": length_bytes,
                            "max_allowed_bytes": settings.max_request_size_bytes,
                        },
                    },
                )

        return await call_next(request)
