"""
Schemas Package
================

Pydantic V2 models for request validation and response serialization.

All schemas are organized by domain concern and re-exported from this package.
"""

from __future__ import annotations

from app.schemas.base import BaseResponse, ErrorResponse, PaginatedResponse
from app.schemas.health import (
    ComponentHealth,
    HealthResponse,
    HealthStatus,
    LivenessResponse,
    ReadinessResponse,
)

__all__ = [
    "BaseResponse",
    "ComponentHealth",
    "ErrorResponse",
    "HealthResponse",
    "HealthStatus",
    "LivenessResponse",
    "PaginatedResponse",
    "ReadinessResponse",
]
