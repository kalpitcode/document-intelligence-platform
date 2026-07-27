"""
Observability & Health API Endpoints Integration Tests
======================================================
"""

from __future__ import annotations

from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient) -> None:
    # 1. Health check
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "components" in data
    assert len(data["components"]) == 7

    # 2. Liveness
    live_resp = await client.get("/api/v1/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["status"] == "alive"

    # 3. Readiness
    ready_resp = await client.get("/api/v1/health/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] in ("ready", "not_ready")


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "blackrock_dip_http_requests_total" in text
    assert "blackrock_dip_database_query_time_seconds" in text


@pytest.mark.asyncio
async def test_system_status_and_diagnostics(client: AsyncClient) -> None:
    # Diagnostics
    diag_resp = await client.get("/api/v1/diagnostics")
    assert diag_resp.status_code == 200
    diag_body = diag_resp.json()
    assert diag_body["data"]["environment"] is not None
    assert "config_validation" in diag_body["data"]

    # System status
    status_resp = await client.get("/api/v1/system/status")
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert "uptime_seconds" in status_body["data"]
    assert "active_connections" in status_body["data"]
