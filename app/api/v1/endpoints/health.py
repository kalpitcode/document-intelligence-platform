"""
Health Check Endpoints Module
==============================

Provides health, readiness, and liveness probes for the platform across all 7 core infrastructure components.

**Architectural Rationale:**
- `/health` — Full system health check. Reports status of Database, Redis, RabbitMQ,
  MinIO, Qdrant, LLM Provider, and Celery Workers.
- `/health/live` — Liveness probe. Returns 200 if process is alive.
- `/health/ready` — Readiness probe. Returns 200 if critical dependencies are ready.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import check_db_health
from app.schemas.health import ComponentHealth, HealthResponse, HealthStatus, LivenessResponse, ReadinessResponse
from app.services.health_service import health_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])

_app_start_time: float = time.time()


def set_app_start_time() -> None:
    global _app_start_time
    _app_start_time = time.time()


@router.get(
    "",
    response_model=HealthResponse,
    summary="System Health Check",
    description="Full system health check including Database, Redis, RabbitMQ, MinIO, Qdrant, LLM Provider, and Celery Workers.",
)
async def health_check() -> HealthResponse:
    settings = get_settings()
    components = await health_service.check_all_components()

    overall_status = HealthStatus.HEALTHY
    if any(c.status != HealthStatus.HEALTHY for c in components):
        overall_status = HealthStatus.DEGRADED
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
    description="Kubernetes liveness probe. Returns 200 if process is alive.",
)
async def liveness() -> LivenessResponse:
    return LivenessResponse(status="alive")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Probe",
    description="Kubernetes readiness probe. Returns 200 if ready to accept traffic.",
)
async def readiness() -> ReadinessResponse:
    components = await health_service.check_all_components()
    checks: dict[str, str] = {c.name: c.status.value for c in components}
    is_ready = all(c.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED) for c in components if c.name in ("database", "redis"))

    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        checks=checks,
    )
