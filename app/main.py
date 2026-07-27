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

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

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

    @application.get("/", include_in_schema=False)
    async def root_portal():
        from fastapi.responses import HTMLResponse
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise AI Document Intelligence Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 40px; max-width: 650px; width: 100%; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); text-align: center; }
        .badge { background: #0284c7; color: #ffffff; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; display: inline-block; margin-bottom: 20px; }
        h1 { font-size: 28px; font-weight: 700; margin-bottom: 12px; color: #ffffff; }
        p { color: #94a3b8; font-size: 15px; line-height: 1.6; margin-bottom: 30px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 30px; }
        .btn { display: flex; align-items: center; justify-content: center; padding: 14px 20px; border-radius: 10px; font-weight: 600; text-decoration: none; transition: all 0.2s ease; font-size: 14px; }
        .btn-primary { background: #2563eb; color: #ffffff; grid-column: span 2; }
        .btn-primary:hover { background: #1d4ed8; transform: translateY(-2px); }
        .btn-secondary { background: #334155; color: #e2e8f0; }
        .btn-secondary:hover { background: #475569; transform: translateY(-2px); }
        .footer { font-size: 12px; color: #64748b; border-top: 1px solid #334155; padding-top: 20px; }
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">Enterprise Production API</span>
        <h1>AI Document Intelligence Platform</h1>
        <p>Production-ready distributed OCR parsing, hybrid vector search, retrieval-augmented generation (RAG), and DAG workflow engine.</p>
        <div class="grid">
            <a href="/api/v1/docs" class="btn btn-primary">🚀 Launch Interactive OpenAPI Docs (Swagger)</a>
            <a href="/api/v1/redoc" class="btn btn-secondary">📘 ReDoc API Specs</a>
            <a href="/api/v1/health" class="btn btn-secondary">💚 System Health Probe</a>
        </div>
        <div class="footer">
            BlackRock Architecture Engine &bull; Environment: Production &bull; Status: Active
        </div>
    </div>
</body>
</html>"""
        return HTMLResponse(content=html_content)

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
