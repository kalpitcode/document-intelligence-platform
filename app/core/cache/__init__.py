"""
Cache Package
==============

Redis connection management for the Document Intelligence Platform.

Usage::

    from app.core.cache import redis_manager

    await redis_manager.init()
    client = redis_manager.get_client()
    await client.set("key", "value")
"""

from __future__ import annotations

from app.core.cache.redis import RedisManager, redis_manager

__all__ = [
    "RedisManager",
    "redis_manager",
]
