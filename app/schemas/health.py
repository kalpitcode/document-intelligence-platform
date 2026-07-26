"""
Health Check Schemas
=====================

Pydantic V2 models for health check endpoint responses.

**Architectural Rationale:**
- Separate schemas for each health check granularity:
  - `HealthResponse` — full system health with component details
  - `LivenessResponse` — simple alive/dead signal
  - `ReadinessResponse` — ready to accept traffic
- Component health is reported individually so monitoring systems
  can alert on specific infrastructure failures.

**Connection to the system:**
- Used as return types for `app.api.v1.endpoints.health` routes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class HealthStatus(StrEnum):
    """Possible health statuses."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class ComponentHealth(BaseModel):
    """Health status of an individual infrastructure component."""

    name: str = Field(description="Component name (e.g., 'database', 'redis')")
    status: HealthStatus = Field(description="Component health status")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional component details",
    )
    response_time_ms: float | None = Field(
        default=None,
        description="Component response time in milliseconds",
    )


class HealthResponse(BaseModel):
    """
    Full system health check response.

    Reports overall system status plus individual component health.
    Used by monitoring dashboards and alerting systems.
    """

    status: HealthStatus = Field(description="Overall system health status")
    version: str = Field(description="Application version")
    environment: str = Field(description="Runtime environment")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Health check timestamp (UTC)",
    )
    components: list[ComponentHealth] = Field(
        default_factory=list,
        description="Individual component health reports",
    )
    uptime_seconds: float | None = Field(
        default=None,
        description="Application uptime in seconds",
    )


class LivenessResponse(BaseModel):
    """
    Liveness probe response.

    Used by Kubernetes/container orchestrators to determine if the
    application process is alive. If this fails, the container is restarted.

    This should NEVER check external dependencies — only that the
    Python process is running and can handle HTTP requests.
    """

    status: str = Field(default="alive", description="Liveness status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Check timestamp (UTC)",
    )


class ReadinessResponse(BaseModel):
    """
    Readiness probe response.

    Used by load balancers to determine if the application is ready
    to accept traffic. Checks critical dependencies (database, cache).
    """

    status: str = Field(description="Readiness status: 'ready' or 'not_ready'")
    checks: dict[str, str] = Field(
        default_factory=dict,
        description="Individual readiness check results",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Check timestamp (UTC)",
    )
