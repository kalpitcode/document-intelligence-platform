"""
Observability Schemas Module
============================

Pydantic V2 schemas for system status, diagnostics, metrics summary, and alert rules.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, Field


class ActiveAlertSchema(BaseModel):
    """Active system alert schema."""
    id: str = Field(..., description="Unique alert ID")
    rule: str = Field(..., description="Alert rule name")
    severity: str = Field(..., description="Severity level: CRITICAL | WARNING | INFO")
    message: str = Field(..., description="Human-readable alert explanation")
    component: str = Field(..., description="Affected infrastructure component")
    triggered_at: datetime = Field(..., description="Timestamp when alert was triggered")


class SystemStatusResponse(BaseModel):
    """Real-time system operational status response schema."""
    environment: str = Field(..., description="Runtime environment")
    version: str = Field(..., description="Platform semantic version")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    cpu_utilization_pct: float = Field(..., description="CPU utilization percentage")
    memory_used_mb: float = Field(..., description="Process memory consumption in MB")
    active_connections: int = Field(..., description="Database active connection count")
    active_alerts: list[ActiveAlertSchema] = Field(default_factory=list, description="Currently active alerts")
    component_health: dict[str, str] = Field(default_factory=dict, description="Summary of component statuses")


class SystemDiagnosticsResponse(BaseModel):
    """Detailed system diagnostic report schema."""
    timestamp: datetime = Field(..., description="Diagnostics timestamp")
    environment: str = Field(..., description="Runtime environment")
    version: str = Field(..., description="Application version")
    config_validation: dict[str, Any] = Field(..., description="Environment and secrets validation result")
    components_detail: list[dict[str, Any]] = Field(..., description="Detailed infrastructure status check")
    metrics_summary: dict[str, Any] = Field(..., description="Summary of request counts, latencies and error rates")
    alerts_active: list[ActiveAlertSchema] = Field(default_factory=list, description="List of active system alerts")
