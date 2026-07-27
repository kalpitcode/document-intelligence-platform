"""
Circuit Breaker Resiliency Module
===================================

Enterprise Circuit Breaker pattern implementation with state machine management.

**Architectural Rationale:**
- Implements `CLOSED` -> `OPEN` -> `HALF_OPEN` state transitions.
- Prevents cascading failures when downstream services (LLM APIs, Qdrant, MinIO) experience outages.
- Tracks metrics via `metrics_registry.circuit_breaker_tripped_total`.
"""

from __future__ import annotations

from enum import StrEnum
import logging
import threading
import time
from typing import Any, Callable

from app.core.config import get_settings
from app.core.observability.metrics import metrics_registry

logger = logging.getLogger(__name__)


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(Exception):
    """Raised when an operation is attempted while the circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """Thread-safe Circuit Breaker instance."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_sec: float = 30.0,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()
        self._lock = threading.Lock()

    def __call__(self, func: Callable) -> Callable:
        """Decorator pattern wrapper."""
        import functools

        if asyncio_is_coroutine_function(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await self.call_async(func, *args, **kwargs)
            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.call_sync(func, *args, **kwargs)
        return sync_wrapper

    def allow_request(self) -> bool:
        with self._lock:
            now = time.time()
            if self.state == CircuitState.OPEN:
                if now - self.last_state_change >= self.recovery_timeout_sec:
                    self.state = CircuitState.HALF_OPEN
                    self.last_state_change = now
                    logger.info(f"CircuitBreaker [{self.name}] transition OPEN -> HALF_OPEN")
                    return True
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.last_state_change = time.time()
                logger.info(f"CircuitBreaker [{self.name}] transition HALF_OPEN -> CLOSED")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def record_failure(self) -> None:
        with self._lock:
            self.failure_count += 1
            now = time.time()
            if self.failure_count >= self.failure_threshold or self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.last_state_change = now
                metrics_registry.circuit_breaker_tripped_total.inc(service_name=self.name)
                logger.error(
                    f"CircuitBreaker [{self.name}] TRIPPED! Transition -> OPEN (Failures: {self.failure_count})"
                )

    def call_sync(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        if not self.allow_request():
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is OPEN.")
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    async def call_async(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        if not self.allow_request():
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is OPEN.")
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise


def asyncio_is_coroutine_function(func: Any) -> bool:
    import asyncio
    return asyncio.iscoroutinefunction(func)


# Default circuit breaker instances
llm_circuit_breaker = CircuitBreaker("llm_provider", failure_threshold=5, recovery_timeout_sec=30.0)
qdrant_circuit_breaker = CircuitBreaker("qdrant_vector", failure_threshold=5, recovery_timeout_sec=30.0)
minio_circuit_breaker = CircuitBreaker("minio_storage", failure_threshold=5, recovery_timeout_sec=30.0)
