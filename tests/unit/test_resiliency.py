"""
Resiliency Unit Tests
=====================
"""

from __future__ import annotations

import asyncio
import pytest

from app.core.resiliency.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState
from app.core.resiliency.retry import with_retry, with_timeout


def test_circuit_breaker_state_transitions() -> None:
    cb = CircuitBreaker("test_cb", failure_threshold=2, recovery_timeout_sec=0.1)
    assert cb.state == CircuitState.CLOSED

    # Failure 1
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED

    # Failure 2 -> TRIPPED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    # Should reject requests when OPEN
    with pytest.raises(CircuitBreakerOpenError):
        cb.call_sync(lambda: "ok")

    # Wait for recovery timeout
    import time
    time.sleep(0.12)

    # Should allow request and transition to HALF_OPEN
    assert cb.allow_request() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Success in HALF_OPEN resets to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_retry_policy_with_fallback() -> None:
    calls = 0

    async def failing_func() -> str:
        nonlocal calls
        calls += 1
        raise ValueError("Temporary failure")

    result = await with_retry(failing_func, max_retries=2, base_delay_sec=0.01, fallback="fallback_val")
    assert result == "fallback_val"
    assert calls == 2


@pytest.mark.asyncio
async def test_timeout_policy_with_fallback() -> None:
    async def slow_func() -> str:
        await asyncio.sleep(0.2)
        return "completed"

    res = await with_timeout(slow_func(), timeout_sec=0.05, fallback="timeout_fallback")
    assert res == "timeout_fallback"
