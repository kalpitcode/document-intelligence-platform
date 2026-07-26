"""
Integration Tests for Users API Endpoints & RBAC
=================================================
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_get_and_update_my_profile(client: AsyncClient) -> None:
    """Test getting and updating profile endpoint."""
    # 1. Register user
    reg_payload = {
        "email": "user_profile@example.com",
        "username": "profileuser",
        "password": "SecurePassword123!",
        "first_name": "Original",
        "last_name": "Name",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201

    # 2. Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email_or_username": "user_profile@example.com", "password": "SecurePassword123!"},
    )
    access_token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Get profile /users/me
    me_res = await client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["first_name"] == "Original"

    # 4. Update profile /users/me
    update_res = await client.put(
        "/api/v1/users/me",
        json={"first_name": "Updated", "last_name": "User"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["first_name"] == "Updated"
    assert update_res.json()["data"]["last_name"] == "User"
