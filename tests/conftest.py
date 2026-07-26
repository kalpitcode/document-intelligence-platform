"""
Test Configuration & Fixtures
================================

Central pytest configuration providing shared fixtures for all tests.
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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Set test environment BEFORE importing app modules
os.environ["APP_ENV"] = "testing"
os.environ["POSTGRES_DB"] = "document_intelligence_test"

from app.core.database.base import Base
from app.core.database.session import get_async_session, get_db_session
from app.models.user import UserModel
from app.repositories.user_repository import UserRepository
from app.services.password_service import PasswordService


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Any:
    """Get test-specific settings."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    return get_settings()


@pytest_asyncio.fixture(scope="session")
async def async_test_engine():
    """Create in-memory SQLite engine for tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide isolated AsyncSession for testing."""
    session_factory = async_sessionmaker(bind=async_test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> UserModel:
    """Create and return a test user instance."""
    user_repo = UserRepository(db_session)
    existing = await user_repo.get_by_email("testuser@blackrock.com")
    if existing:
        return existing

    user_data = {
        "email": "testuser@blackrock.com",
        "username": "testuser",
        "hashed_password": PasswordService.hash_password("Password123!"),
        "first_name": "Test",
        "last_name": "User",
        "is_active": True,
        "email_verified": True,
    }
    user = await user_repo.create(**user_data)
    await db_session.commit()
    return user


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP client for testing API endpoints with in-memory DB session override.
    """
    with (
        patch("app.core.database.session.init_db", new_callable=AsyncMock),
        patch("app.core.database.session.close_db", new_callable=AsyncMock),
        patch("app.core.cache.redis.RedisManager.init", new_callable=AsyncMock),
        patch("app.core.cache.redis.RedisManager.close", new_callable=AsyncMock),
        patch("app.core.cache.redis.RedisManager.health_check", AsyncMock(return_value={"status": "healthy"})),
        patch("app.core.messaging.rabbitmq.RabbitMQManager.init", new_callable=AsyncMock),
        patch("app.core.messaging.rabbitmq.RabbitMQManager.close", new_callable=AsyncMock),
        patch("app.core.messaging.rabbitmq.RabbitMQManager.health_check", AsyncMock(return_value={"status": "healthy"})),
        patch("app.core.database.check_db_health", AsyncMock(return_value={"status": "healthy"})),
        patch("app.api.v1.endpoints.health.check_db_health", AsyncMock(return_value={"status": "healthy"})),
    ):
        from app.core.config import get_settings
        get_settings.cache_clear()

        from app.main import create_application

        app = create_application()

        async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
            try:
                yield db_session
                await db_session.commit()
            except Exception:
                await db_session.rollback()
                raise

        app.dependency_overrides[get_db_session] = _override_get_db
        app.dependency_overrides[get_async_session] = _override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as ac:
            yield ac

        app.dependency_overrides.clear()
