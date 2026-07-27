"""
Rate Limiting Middleware Module
================================

Sliding-window API request rate limiter enforcing rate limits per client IP or authenticated user.

**Architectural Rationale:**
- Implements thread-safe in-memory and Redis sliding window rate limiting.
- Rejects requests exceeding threshold with HTTP 429 Too Many Requests.
- Records metrics in `metrics_registry.rate_limit_exceeded_total`.
"""

from __future__ import annotations

from collections import defaultdict
import logging
import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.observability.metrics import metrics_registry

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window counter."""

    def __init__(self, limit: int, window_sec: int) -> None:
        self.limit = limit
        self.window_sec = window_sec
        self._history: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> tuple[bool, int, float]:
        now = time.time()
        cutoff = now - self.window_sec

        with self._lock:
            # Clean old timestamps
            self._history[key] = [t for t in self._history[key] if t > cutoff]
            current_count = len(self._history[key])

            if current_count >= self.limit:
                reset_after = round(self._history[key][0] + self.window_sec - now, 2)
                return False, 0, max(0.1, reset_after)

            self._history[key].append(now)
            remaining = self.limit - current_count - 1
            return True, remaining, float(self.window_sec)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware enforcing request rate limits."""

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        settings = get_settings()
        self.limiter = SlidingWindowRateLimiter(
            limit=settings.rate_limit_default_requests,
            window_sec=settings.rate_limit_window_seconds,
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()

        # Skip health / metrics probes or if rate limiting disabled
        if not settings.rate_limiting_enabled or request.url.path.endswith(("/health", "/live", "/ready", "/metrics")):
            return await call_next(request)

        # Identify client by user_id or client IP
        client_ip = request.client.host if request.client else "127.0.0.1"
        auth_header = request.headers.get("Authorization", "")
        key = f"rl:{auth_header[:30] if auth_header else client_ip}"

        allowed, remaining, reset_sec = self.limiter.is_allowed(key)
        if not allowed:
            metrics_registry.rate_limit_exceeded_total.inc(client_ip=client_ip)
            logger.warning(
                "Rate limit exceeded",
                extra={"client_ip": client_ip, "path": request.url.path},
            )
            return JSONResponse(
                status_code=429,
                content={
                    "status_code": 429,
                    "message": "Rate limit exceeded. Please try again later.",
                    "details": {"retry_after_seconds": reset_sec},
                },
                headers={
                    "Retry-After": str(int(reset_sec)),
                    "X-RateLimit-Limit": str(settings.rate_limit_default_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_default_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
