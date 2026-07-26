"""
Dependencies Package
=====================

Central dependency injection container for FastAPI.

**Architectural Rationale:**
- All FastAPI `Depends()` callables are defined or re-exported here.
- Route handlers import dependencies from this single location.
- This decouples route handlers from concrete implementations,
  making services easily swappable for testing.

**Connection to the system:**
- Imported by route handlers via `from app.dependencies import get_db_session`.
"""

from __future__ import annotations

from app.core.cache.redis import redis_manager
from app.core.database.session import get_db_session


async def get_redis():  # type: ignore[no-untyped-def]
    """
    FastAPI dependency that provides a Redis client.

    Usage::

        @router.get("/cached")
        async def get_cached(redis = Depends(get_redis)):
            value = await redis.get("key")
    """
    return redis_manager.get_client()


__all__ = [
    "get_db_session",
    "get_redis",
]
