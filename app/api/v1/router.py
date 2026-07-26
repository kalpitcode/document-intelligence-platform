"""
API V1 Router
===============

Aggregates all v1 sub-routers into a single versioned router.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.root import router as root_router
from app.api.v1.endpoints.users import router as users_router

# Create the v1 API router
api_v1_router = APIRouter()

# --- Register sub-routers ---
api_v1_router.include_router(root_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
