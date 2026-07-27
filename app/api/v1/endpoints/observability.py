"""
Observability API Endpoints Module
===================================

Production endpoints exposing:
- Prometheus Metrics (`GET /api/v1/metrics`)
- System Self-Diagnostics (`GET /api/v1/diagnostics`)
- Real-Time System Status (`GET /api/v1/system/status`)

**Architectural Rationale:**
- Serves Prometheus OpenMetrics text format directly on `/metrics` and `/api/v1/metrics`.
- Returns structured JSON system status and diagnostics for monitoring portals.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Response, status

from app.core.observability.metrics import metrics_registry
from app.schemas.base import APIResponse
from app.schemas.observability import SystemDiagnosticsResponse, SystemStatusResponse
from app.services.diagnostics_service import diagnostics_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Observability & Operational Excellence"])


@router.get(
    "/metrics",
    summary="Export Prometheus Metrics",
    description="Expose all platform operational metrics in standard OpenMetrics text format.",
    response_class=Response,
)
async def get_prometheus_metrics() -> Response:
    """Return standard Prometheus exposition text format."""
    text_data = metrics_registry.generate_prometheus_text()
    return Response(content=text_data, media_type="text/plain; version=0.0.4; charset=utf-8")


@router.get(
    "/diagnostics",
    response_model=APIResponse[SystemDiagnosticsResponse],
    summary="System Self-Diagnostics",
    description="Run comprehensive system self-diagnostics, secret strength validations, component probes, and active alert evaluation.",
)
async def get_system_diagnostics() -> APIResponse[SystemDiagnosticsResponse]:
    """Retrieve full system diagnostics report."""
    report = await diagnostics_service.run_diagnostics()
    return APIResponse(
        data=report,
        message="System self-diagnostics completed successfully",
    )


@router.get(
    "/system/status",
    response_model=APIResponse[SystemStatusResponse],
    summary="Real-Time System Status",
    description="Fetch current operational status, process resource utilization, database pool connections, and active alerts.",
)
async def get_system_status() -> APIResponse[SystemStatusResponse]:
    """Retrieve real-time platform system status."""
    status_data = await diagnostics_service.get_system_status()
    return APIResponse(
        data=status_data,
        message="System status retrieved successfully",
    )
