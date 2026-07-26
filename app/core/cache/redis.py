"""
Redis Connection Manager
=========================

Manages the async Redis connection lifecycle, health checks, and DI.

**Architectural Rationale:**
- Encapsulates all Redis concerns in a single manager class (SRP).
- Connection pool is created once during app startup, shared across requests.
- Health check verifies connectivity for the `/health` endpoint.
- Uses `redis.asyncio` for non-blocking operations consistent with our async stack.
- Connection is dependency-injected via FastAPI's `Depends()`.

**Connection to the system:**
- `init()` / `close()` called by app startup/shutdown events in `app.main`.
- `get_client()` used as a FastAPI dependency wherever Redis is needed.
- `health_check()` called by the health endpoint.
"""

from __future__ import annotations

import logging
from typing import Any

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Manages the Redis connection pool and client lifecycle.

    Usage::

        redis_manager = RedisManager()
        await redis_manager.init()

        client = redis_manager.get_client()
        await client.set("key", "value")

        await redis_manager.close()
    """

    def __init__(self) -> None:
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None  # type: ignore[type-arg]

    async def init(self) -> None:
        """
        Initialize the Redis connection pool and client.

        Reads configuration from application settings.
        """
        settings = get_settings()

        self._pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
            retry_on_timeout=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )

        self._client = Redis(connection_pool=self._pool)

        logger.info(
            "Redis connection pool initialized",
            extra={
                "host": settings.redis_host,
                "port": settings.redis_port,
                "db": settings.redis_db,
                "max_connections": settings.redis_max_connections,
            },
        )

    async def close(self) -> None:
        """Close the Redis client and connection pool."""
        if self._client is not None:
            await self._client.close()
            logger.info("Redis connection closed")

        if self._pool is not None:
            await self._pool.disconnect()

        self._client = None
        self._pool = None

    def get_client(self) -> Redis:  # type: ignore[type-arg]
        """
        Get the Redis client instance.

        Returns:
            The active Redis client.

        Raises:
            RuntimeError: If the manager has not been initialized.
        """
        if self._client is None:
            msg = "Redis not initialized. Call init() first."
            raise RuntimeError(msg)
        return self._client

    async def health_check(self) -> dict[str, Any]:
        """
        Verify Redis connectivity.

        Returns:
            Dictionary with connection status.
        """
        if self._client is None:
            return {"status": "unhealthy", "error": "Client not initialized"}

        try:
            pong = await self._client.ping()
            if pong:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": "PING returned False"}
        except Exception as exc:
            logger.error("Redis health check failed", exc_info=exc)
            return {"status": "unhealthy", "error": str(exc)}


# Module-level singleton instance
redis_manager = RedisManager()
