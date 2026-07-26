"""
Root API Endpoints
===================

Provides the root welcome endpoint and version information.

**Architectural Rationale:**
- The root endpoint serves as a lightweight discovery point for the API.
- The version endpoint enables clients and CI/CD pipelines to verify
  which version of the API is deployed.
- Both endpoints require no authentication and serve as a quick
  connectivity check.

**Connection to the system:**
- Registered on the v1 router in `app.api.v1.router`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.base import BaseResponse

router = APIRouter(tags=["Root"])


@router.get(
    "/",
    response_model=BaseResponse[dict],
    summary="API Root",
    description="Welcome endpoint with API information.",
)
async def root() -> BaseResponse[dict]:
    """
    API root endpoint.

    Returns basic API information including name, version,
    description, and documentation URL.
    """
    settings = get_settings()

    return BaseResponse(
        success=True,
        message="Welcome to the Document Intelligence Platform API",
        data={
            "name": settings.app_name,
            "version": settings.app_version,
            "description": settings.app_description,
            "environment": settings.app_env,
            "docs_url": f"{settings.api_v1_prefix}/docs",
            "health_url": f"{settings.api_v1_prefix}/health",
        },
    )


@router.get(
    "/version",
    response_model=BaseResponse[dict],
    summary="API Version",
    description="Returns the current API version and build information.",
)
async def version() -> BaseResponse[dict]:
    """
    Version endpoint.

    Returns the application version and runtime metadata.
    Useful for deployment verification and debugging.
    """
    settings = get_settings()

    return BaseResponse(
        success=True,
        message="Version information",
        data={
            "version": settings.app_version,
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "python_version": "3.12",
            "framework": "FastAPI",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
