"""
Application Factory
=====================

Creates and configures the FastAPI application instance.

**Architectural Rationale:**
- The application factory pattern (`create_application()`) enables:
  - Multiple app instances for testing with different configurations.
  - Clean separation between app creation and app startup.
  - Explicit, reviewable startup and shutdown sequences.
- Startup events initialize infrastructure (DB, Redis, RabbitMQ).
- Shutdown events cleanly close connections to prevent resource leaks.
- ORJSON is used as the default response class for ~3x faster JSON serialization.

**Connection to the system:**
- This is the entry point for the entire application.
- Uvicorn loads `app.main:app` (the module-level `app` instance).
- Docker/scripts reference this module for startup.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_v1_router
from app.core.cache import redis_manager
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.messaging import rabbitmq_manager
from app.middlewares import register_middleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    Uses the modern lifespan context manager pattern (replaces
    deprecated on_event decorators).

    Startup:
        1. Configure logging
        2. Initialize database connection pool
        3. Initialize Redis connection pool
        4. Initialize RabbitMQ connection

    Shutdown:
        1. Close RabbitMQ connection
        2. Close Redis connection pool
        3. Close database connection pool
    """
    settings = get_settings()

    # --- STARTUP ---
    logger.info(
        "Starting %s v%s [%s]",
        settings.app_name,
        settings.app_version,
        settings.app_env,
    )

    # Initialize infrastructure
    await init_db()
    await redis_manager.init()
    await rabbitmq_manager.init()

    # Set app start time for health endpoint uptime
    from app.api.v1.endpoints.health import set_app_start_time

    set_app_start_time()

    logger.info("Application startup complete")

    yield

    # --- SHUTDOWN ---
    logger.info("Shutting down application...")

    await rabbitmq_manager.close()
    await redis_manager.close()
    await close_db()

    logger.info("Application shutdown complete")


def create_application() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI app.

    Returns:
        Fully configured FastAPI application instance.
    """
    settings = get_settings()

    # Configure logging first (before anything else logs)
    setup_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
        log_file=settings.log_file,
    )

    # Create FastAPI instance
    application = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        debug=settings.app_debug,
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # Register middleware stack
    register_middleware(application)

    # Register global exception handlers
    register_exception_handlers(application)

    # Register API routers
    application.include_router(
        api_v1_router,
        prefix=settings.api_v1_prefix,
    )

    # Mount static assets directory for web UI
    static_dir = Path("app/static")
    if static_dir.exists():
        application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    from app.api.v1.endpoints.web_ui import router as web_ui_router
    application.include_router(web_ui_router)

    logger.info(
        "Application factory complete",
        extra={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "debug": settings.app_debug,
        },
    )

    return application


# Module-level application instance — loaded by Uvicorn
app = create_application()
