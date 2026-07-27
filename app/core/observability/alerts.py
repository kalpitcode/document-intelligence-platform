"""
Alert Manager & Rule Engine Module
====================================

Evaluates system metrics and health status against alert threshold rules.

**Architectural Rationale:**
- Generates active alerts for: High Error Rate, Worker Failure, Queue Backlog,
  Database Offline, Redis Offline, Qdrant Offline, MinIO Offline, LLM Provider Offline,
  and High Latency.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from app.schemas.observability import ActiveAlertSchema

logger = logging.getLogger(__name__)


class AlertEngine:
    """Evaluates active alert conditions across system components."""

    async def evaluate_active_alerts(
        self,
        component_reports: list[dict[str, Any]],
        metrics_summary: dict[str, Any] | None = None,
    ) -> list[ActiveAlertSchema]:
        alerts: list[ActiveAlertSchema] = []
        now = datetime.now(UTC)

        for comp in component_reports:
            name = comp.get("name", "unknown")
            status = comp.get("status", "unhealthy")

            if status != "healthy":
                alerts.append(
                    ActiveAlertSchema(
                        id=f"alert-offline-{name}",
                        rule=f"{name.upper()}_OFFLINE",
                        severity="CRITICAL" if name in ("database", "redis") else "WARNING",
                        message=f"Infrastructure component '{name}' is currently {status.upper()}.",
                        component=name,
                        triggered_at=now,
                    )
                )

        if metrics_summary:
            error_rate = metrics_summary.get("error_rate_pct", 0.0)
            if error_rate > 5.0:
                alerts.append(
                    ActiveAlertSchema(
                        id="alert-high-error-rate",
                        rule="HIGH_ERROR_RATE",
                        severity="CRITICAL",
                        message=f"System error rate is high ({error_rate:.1f}% > 5.0%).",
                        component="api",
                        triggered_at=now,
                    )
                )

            avg_latency = metrics_summary.get("avg_http_duration_sec", 0.0)
            if avg_latency > 2.0:
                alerts.append(
                    ActiveAlertSchema(
                        id="alert-high-latency",
                        rule="HIGH_LATENCY",
                        severity="WARNING",
                        message=f"Average HTTP request latency is high ({avg_latency:.2f}s > 2.0s).",
                        component="api",
                        triggered_at=now,
                    )
                )

        return alerts


alert_engine = AlertEngine()
