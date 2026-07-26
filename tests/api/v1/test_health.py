"""
Health Endpoint Tests
======================

Tests for the health, liveness, and readiness endpoints.

These tests verify that:
1. Health endpoints return correct status codes.
2. Response schemas match the Pydantic models.
3. Component health is reported with correct structure.
4. Liveness probe returns 200 unconditionally.
5. Readiness probe checks critical dependencies.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Tests for the /api/v1/health endpoint."""

    async def test_health_check_returns_200(self, client: AsyncClient) -> None:
        """Health endpoint should return 200 with component details."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "components" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data

    async def test_health_check_includes_components(self, client: AsyncClient) -> None:
        """Health response should include individual component health."""
        response = await client.get("/api/v1/health")
        data = response.json()

        components = data["components"]
        assert len(components) >= 3  # database, redis, rabbitmq

        component_names = [c["name"] for c in components]
        assert "database" in component_names
        assert "redis" in component_names
        assert "rabbitmq" in component_names

    async def test_health_check_component_structure(self, client: AsyncClient) -> None:
        """Each component should have the expected fields."""
        response = await client.get("/api/v1/health")
        data = response.json()

        for component in data["components"]:
            assert "name" in component
            assert "status" in component
            assert "details" in component
            assert "response_time_ms" in component

    async def test_health_check_reports_version(self, client: AsyncClient) -> None:
        """Health endpoint should report the application version."""
        response = await client.get("/api/v1/health")
        data = response.json()
        assert data["version"] == "0.1.0"


@pytest.mark.asyncio
class TestLivenessEndpoint:
    """Tests for the /api/v1/health/live endpoint."""

    async def test_liveness_returns_200(self, client: AsyncClient) -> None:
        """Liveness probe should always return 200."""
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200

    async def test_liveness_returns_alive_status(self, client: AsyncClient) -> None:
        """Liveness response should have status 'alive'."""
        response = await client.get("/api/v1/health/live")
        data = response.json()
        assert data["status"] == "alive"

    async def test_liveness_includes_timestamp(self, client: AsyncClient) -> None:
        """Liveness response should include a timestamp."""
        response = await client.get("/api/v1/health/live")
        data = response.json()
        assert "timestamp" in data


@pytest.mark.asyncio
class TestReadinessEndpoint:
    """Tests for the /api/v1/health/ready endpoint."""

    async def test_readiness_returns_200(self, client: AsyncClient) -> None:
        """Readiness probe should return 200 when all dependencies are healthy."""
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 200

    async def test_readiness_returns_ready_status(self, client: AsyncClient) -> None:
        """Readiness response should have status 'ready' when healthy."""
        response = await client.get("/api/v1/health/ready")
        data = response.json()
        assert data["status"] == "ready"

    async def test_readiness_includes_checks(self, client: AsyncClient) -> None:
        """Readiness response should include individual check results."""
        response = await client.get("/api/v1/health/ready")
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
