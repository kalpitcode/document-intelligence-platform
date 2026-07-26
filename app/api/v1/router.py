"""
API V1 Router
===============

Aggregates all v1 sub-routers into a single versioned router.

**Architectural Rationale:**
- Versioned routing (`/api/v1/`) enables non-breaking API evolution.
- Each feature area has its own router module for separation of concerns.
- New feature routers are added here as a single `include_router()` call.
- Router tags organize the OpenAPI documentation by domain.

**Connection to the system:**
- Included in the main application via `app.main.create_application()`.
- Each endpoint module defines its own `router` instance.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.root import router as root_router

# Create the v1 API router
api_v1_router = APIRouter()

# --- Register sub-routers ---
api_v1_router.include_router(root_router)
api_v1_router.include_router(health_router)

# Future routers will be added here:
# api_v1_router.include_router(documents_router)
# api_v1_router.include_router(search_router)
# api_v1_router.include_router(users_router)
