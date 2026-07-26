"""
Integration Tests for Auth & Users API Endpoints
=================================================
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_and_login_flow(client: AsyncClient) -> None:
    """Test full user registration, login, profile fetch, and logout flow."""
    # 1. Register user
    reg_payload = {
        "email": "testuser_iam@example.com",
        "username": "testuser_iam",
        "password": "SecurePassword123!",
        "first_name": "Test",
        "last_name": "User",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["success"] is True
    assert reg_data["data"]["email"] == "testuser_iam@example.com"

    # 2. Login user
    login_payload = {
        "email_or_username": "testuser_iam@example.com",
        "password": "SecurePassword123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["success"] is True
    access_token = login_data["data"]["access_token"]
    refresh_token = login_data["data"]["refresh_token"]

    # 3. Get profile /auth/me
    headers = {"Authorization": f"Bearer {access_token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["username"] == "testuser_iam"

    # 4. Refresh token
    ref_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 200
    assert "access_token" in ref_res.json()["data"]

    # 5. Logout
    logout_res = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token}, headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["data"]["logged_out"] is True


async def test_invalid_login_credentials(client: AsyncClient) -> None:
    """Test login rejection for wrong password."""
    res = await client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "nonexistent@example.com", "password": "WrongPassword123!"},
    )
    assert res.status_code == 401
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
