"""
Database Session Module
========================

Manages the async SQLAlchemy engine, session factory, and dependency injection.

**Architectural Rationale:**
- The engine is created once during app startup and closed during shutdown.
- `async_sessionmaker` produces sessions that are request-scoped via
  FastAPI's dependency injection (`get_db_session` generator).
- Connection pooling is configured from settings (pool_size, max_overflow,
  pool_recycle) for production-grade connection management.
- The session is committed on success and rolled back on exception —
  enforced by the context manager pattern.

**Connection to the system:**
- `init_db()` / `close_db()` are called by app startup/shutdown events.
- `get_db_session()` is injected into route handlers via `Depends()`.
- Health check uses `check_db_health()` to verify connectivity.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Module-level references — initialized during app startup.
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """
    Initialize the database engine and session factory.

    Called once during application startup. Configures connection pooling
    based on application settings.
    """
    global _engine, _session_factory

    settings = get_settings()

    engine_kwargs: dict[str, Any] = {
        "echo": settings.postgres_echo,
        "pool_pre_ping": True,  # Verify connections before use
    }

    # Use NullPool for testing to avoid connection leaks
    if settings.is_testing:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs.update(
            {
                "pool_size": settings.postgres_pool_size,
                "max_overflow": settings.postgres_max_overflow,
                "pool_recycle": settings.postgres_pool_recycle,
            }
        )

    _engine = create_async_engine(settings.database_url, **engine_kwargs)

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    logger.info(
        "Database engine initialized",
        extra={
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "database": settings.postgres_db,
            "pool_size": settings.postgres_pool_size if not settings.is_testing else "NullPool",
        },
    )


async def close_db() -> None:
    """
    Close the database engine and release all connections.

    Called during application shutdown.
    """
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine closed")

    _engine = None
    _session_factory = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Yields an `AsyncSession` that is automatically committed on success
    and rolled back on exception. The session is always closed after use.

    Usage::

        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    if _session_factory is None:
        msg = "Database not initialized. Call init_db() first."
        raise RuntimeError(msg)

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
            await session.close()


# Alias for dependency injection compatibility
get_async_session = get_db_session


async def check_db_health() -> dict[str, Any]:
    """
    Verify database connectivity for the health endpoint.

    Returns:
        Dictionary with connection status and details.
    """
    if _engine is None:
        return {"status": "unhealthy", "error": "Engine not initialized"}

    try:
        async with _engine.connect() as conn:
            result = await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
            result.close()
        return {"status": "healthy"}
    except Exception as exc:
        logger.error("Database health check failed", exc_info=exc)
        return {"status": "unhealthy", "error": str(exc)}


def get_engine() -> AsyncEngine | None:
    """Get the current database engine instance."""
    return _engine
