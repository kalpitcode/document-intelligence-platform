"""
Health Check Endpoints
=======================

Provides health, readiness, and liveness probes for the platform.

**Architectural Rationale:**
- `/health` — Full system health check. Reports status of every
  infrastructure component (DB, Redis, RabbitMQ). Used by monitoring
  dashboards and alerting systems.
- `/health/live` — Liveness probe. Returns 200 if the Python process
  is alive. Used by Kubernetes to decide whether to restart the container.
  MUST NOT check external dependencies.
- `/health/ready` — Readiness probe. Returns 200 if the app is ready
  to accept traffic (DB connected, cache available). Used by load
  balancers to route traffic.

**Connection to the system:**
- Registered on the v1 router in `app.api.v1.router`.
- Calls health check methods on database, Redis, and RabbitMQ managers.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from app.core.cache import redis_manager
from app.core.config import get_settings
from app.core.database import check_db_health
from app.core.messaging import rabbitmq_manager
from app.schemas.health import (
    ComponentHealth,
    HealthResponse,
    HealthStatus,
    LivenessResponse,
    ReadinessResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])

# Track application start time for uptime calculation
_app_start_time: float = time.time()


def set_app_start_time() -> None:
    """Set the application start time. Called during startup."""
    global _app_start_time
    _app_start_time = time.time()


@router.get(
    "",
    response_model=HealthResponse,
    summary="System Health Check",
    description="Full system health check including all infrastructure components.",
)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check endpoint.

    Checks connectivity and status of:
    - PostgreSQL database
    - Redis cache
    - RabbitMQ message broker

    Returns overall system status based on component health.
    """
    settings = get_settings()
    components: list[ComponentHealth] = []
    overall_status = HealthStatus.HEALTHY

    # --- Database Health ---
    start = time.perf_counter()
    db_health = await check_db_health()
    db_time = round((time.perf_counter() - start) * 1000, 2)
    db_status = HealthStatus(db_health.get("status", "unhealthy"))
    components.append(
        ComponentHealth(
            name="database",
            status=db_status,
            details=db_health,
            response_time_ms=db_time,
        )
    )
    if db_status != HealthStatus.HEALTHY:
        overall_status = HealthStatus.DEGRADED

    # --- Redis Health ---
    start = time.perf_counter()
    redis_health = await redis_manager.health_check()
    redis_time = round((time.perf_counter() - start) * 1000, 2)
    redis_status = HealthStatus(redis_health.get("status", "unhealthy"))
    components.append(
        ComponentHealth(
            name="redis",
            status=redis_status,
            details=redis_health,
            response_time_ms=redis_time,
        )
    )
    if redis_status != HealthStatus.HEALTHY:
        overall_status = HealthStatus.DEGRADED

    # --- RabbitMQ Health ---
    start = time.perf_counter()
    rabbitmq_health = await rabbitmq_manager.health_check()
    rabbitmq_time = round((time.perf_counter() - start) * 1000, 2)
    rabbitmq_status = HealthStatus(rabbitmq_health.get("status", "unhealthy"))
    components.append(
        ComponentHealth(
            name="rabbitmq",
            status=rabbitmq_status,
            details=rabbitmq_health,
            response_time_ms=rabbitmq_time,
        )
    )
    if rabbitmq_status != HealthStatus.HEALTHY:
        overall_status = HealthStatus.DEGRADED

    # If ALL components are unhealthy, system is unhealthy
    if all(c.status == HealthStatus.UNHEALTHY for c in components):
        overall_status = HealthStatus.UNHEALTHY

    uptime = round(time.time() - _app_start_time, 2)

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.app_env,
        components=components,
        uptime_seconds=uptime,
    )


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness Probe",
    description="Kubernetes liveness probe. Returns 200 if the process is alive.",
)
async def liveness() -> LivenessResponse:
    """
    Liveness probe — confirms the application process is running.

    This endpoint MUST NOT check external dependencies.
    If this fails, the orchestrator restarts the container.
    """
    return LivenessResponse(status="alive")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Probe",
    description="Kubernetes readiness probe. Returns 200 if ready to accept traffic.",
)
async def readiness() -> ReadinessResponse:
    """
    Readiness probe — confirms the application can accept traffic.

    Checks critical dependencies. If not ready, the load balancer
    stops routing traffic to this instance.
    """
    checks: dict[str, str] = {}
    is_ready = True

    # Check database
    db_health = await check_db_health()
    checks["database"] = db_health.get("status", "unhealthy")
    if checks["database"] != "healthy":
        is_ready = False

    # Check Redis
    redis_health = await redis_manager.health_check()
    checks["redis"] = redis_health.get("status", "unhealthy")
    if checks["redis"] != "healthy":
        is_ready = False

    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        checks=checks,
    )
