"""
Retry Policies & Timeout Utilities Module
==========================================

Universal async `with_retry` and `with_timeout` helper functions with fallback strategies.

**Architectural Rationale:**
- Implements exponential backoff, configurable max attempts, and fallback results.
- Wraps execution with timeout enforcement.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import logging
import math
import time
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_retry(
    func: Callable[..., Awaitable[T]],
    max_retries: int = 3,
    base_delay_sec: float = 0.5,
    exponential: bool = True,
    fallback: T | None = None,
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Execute async coroutine with retries and fallback strategy.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt == max_retries:
                logger.error(f"Retry limit ({max_retries}) reached for {func.__name__}: {exc}")
                if fallback is not None:
                    return fallback
                raise exc

            delay = base_delay_sec * (2 ** (attempt - 1)) if exponential else base_delay_sec
            logger.warning(f"Attempt {attempt} failed for {func.__name__}: {exc}. Retrying in {delay:.2f}s...")
            await asyncio.sleep(delay)

    if fallback is not None:
        return fallback
    assert last_exc is not None
    raise last_exc


async def with_timeout(
    coro: Awaitable[T],
    timeout_sec: float,
    fallback: T | None = None,
) -> T:
    """
    Enforce hard timeout on coroutine execution.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_sec)
    except asyncio.TimeoutError as exc:
        logger.error(f"Operation timed out after {timeout_sec} seconds")
        if fallback is not None:
            return fallback
        raise exc
