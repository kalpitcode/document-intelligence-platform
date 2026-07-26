"""
Test Configuration & Fixtures
================================

Central pytest configuration providing shared fixtures for all tests.

**Architectural Rationale:**
- The `test_app` fixture creates a fresh FastAPI application for each
  test session, ensuring test isolation.
- The `client` fixture provides an async HTTP client (httpx) that
  sends requests to the test app without starting a real server.
- Settings are overridden to use test-specific configuration
  (separate database, reduced pool sizes, etc.).
- Database fixtures provide isolated sessions with automatic rollback.

**Connection to the system:**
- All test modules automatically use fixtures defined here.
- Uses `TestingSettings` for environment isolation.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Set test environment BEFORE importing app modules
os.environ["APP_ENV"] = "testing"
os.environ["POSTGRES_DB"] = "document_intelligence_test"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create a single event loop for the entire test session.

    This prevents issues with multiple event loops when running
    async tests.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Any:
    """
    Get test-specific settings.

    Returns the TestingSettings configuration instance.
    """
    from app.core.config import get_settings

    # Clear lru_cache to force reload with test env
    get_settings.cache_clear()
    settings = get_settings()
    return settings


@pytest.fixture()
def mock_db_health() -> AsyncMock:
    """Mock database health check for tests without a real database."""
    mock = AsyncMock(return_value={"status": "healthy"})
    return mock


@pytest.fixture()
def mock_redis_health() -> AsyncMock:
    """Mock Redis health check for tests without a real Redis instance."""
    mock = AsyncMock(return_value={"status": "healthy"})
    return mock


@pytest.fixture()
def mock_rabbitmq_health() -> AsyncMock:
    """Mock RabbitMQ health check for tests without a real RabbitMQ instance."""
    mock = AsyncMock(return_value={"status": "healthy"})
    return mock


@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP client for testing API endpoints.

    Mocks all infrastructure connections (DB, Redis, RabbitMQ)
    so tests can run without external dependencies.
    """
    # Mock infrastructure to avoid requiring real services
    with (
        patch("app.core.database.session.init_db", new_callable=AsyncMock),
        patch("app.core.database.session.close_db", new_callable=AsyncMock),
        patch("app.core.cache.redis.RedisManager.init", new_callable=AsyncMock),
        patch("app.core.cache.redis.RedisManager.close", new_callable=AsyncMock),
        patch(
            "app.core.cache.redis.RedisManager.health_check",
            new_callable=AsyncMock,
            return_value={"status": "healthy"},
        ),
        patch("app.core.messaging.rabbitmq.RabbitMQManager.init", new_callable=AsyncMock),
        patch("app.core.messaging.rabbitmq.RabbitMQManager.close", new_callable=AsyncMock),
        patch(
            "app.core.messaging.rabbitmq.RabbitMQManager.health_check",
            new_callable=AsyncMock,
            return_value={"status": "healthy"},
        ),
        patch(
            "app.core.database.session.check_db_health",
            new_callable=AsyncMock,
            return_value={"status": "healthy"},
        ),
        patch(
            "app.api.v1.endpoints.health.check_db_health",
            new_callable=AsyncMock,
            return_value={"status": "healthy"},
        ),
    ):
        # Clear settings cache to ensure test settings are loaded
        from app.core.config import get_settings

        get_settings.cache_clear()

        from app.main import create_application

        app = create_application()

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as ac:
            yield ac
