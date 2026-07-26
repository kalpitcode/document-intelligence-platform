"""
Root Endpoint Tests
====================

Tests for the root (/) and version (/version) endpoints.

These tests verify that:
1. Root endpoint returns API information.
2. Version endpoint returns correct version.
3. Response schemas follow the standard BaseResponse envelope.
4. Response headers include request ID and processing time.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRootEndpoint:
    """Tests for the /api/v1/ endpoint."""

    async def test_root_returns_200(self, client: AsyncClient) -> None:
        """Root endpoint should return 200."""
        response = await client.get("/api/v1/")
        assert response.status_code == 200

    async def test_root_returns_success_envelope(self, client: AsyncClient) -> None:
        """Root response should follow BaseResponse schema."""
        response = await client.get("/api/v1/")
        data = response.json()

        assert data["success"] is True
        assert "message" in data
        assert "data" in data
        assert "timestamp" in data

    async def test_root_returns_api_info(self, client: AsyncClient) -> None:
        """Root response data should include API metadata."""
        response = await client.get("/api/v1/")
        data = response.json()["data"]

        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "environment" in data

    async def test_root_response_has_request_id_header(self, client: AsyncClient) -> None:
        """Response should include X-Request-ID header."""
        response = await client.get("/api/v1/")
        assert "x-request-id" in response.headers

    async def test_root_response_has_process_time_header(self, client: AsyncClient) -> None:
        """Response should include X-Process-Time header."""
        response = await client.get("/api/v1/")
        assert "x-process-time" in response.headers

    async def test_root_honors_client_request_id(self, client: AsyncClient) -> None:
        """If client sends X-Request-ID, it should be echoed back."""
        custom_id = "test-request-id-12345"
        response = await client.get(
            "/api/v1/",
            headers={"X-Request-ID": custom_id},
        )
        assert response.headers["x-request-id"] == custom_id


@pytest.mark.asyncio
class TestVersionEndpoint:
    """Tests for the /api/v1/version endpoint."""

    async def test_version_returns_200(self, client: AsyncClient) -> None:
        """Version endpoint should return 200."""
        response = await client.get("/api/v1/version")
        assert response.status_code == 200

    async def test_version_returns_correct_version(self, client: AsyncClient) -> None:
        """Version response should include the application version."""
        response = await client.get("/api/v1/version")
        data = response.json()["data"]
        assert data["version"] == "0.1.0"

    async def test_version_includes_framework_info(self, client: AsyncClient) -> None:
        """Version response should include framework metadata."""
        response = await client.get("/api/v1/version")
        data = response.json()["data"]
        assert data["framework"] == "FastAPI"
        assert data["python_version"] == "3.12"
