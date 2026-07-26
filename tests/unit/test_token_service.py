"""
Unit Tests for TokenService
=============================
"""

from __future__ import annotations

import pytest

from app.core.exceptions.base import AuthenticationException
from app.services.token_service import TokenService


def test_access_token_creation_and_decoding() -> None:
    """Test access token issuance and claims parsing."""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    token = TokenService.create_access_token(
        user_id=user_id,
        username="testuser",
        email="testuser@example.com",
        token_version=1,
        roles=["User"],
        permissions=["documents.read"],
    )

    payload = TokenService.decode_token(token, expected_type="access")
    assert payload["sub"] == user_id
    assert payload["username"] == "testuser"
    assert payload["roles"] == ["User"]
    assert payload["permissions"] == ["documents.read"]


def test_refresh_token_creation_and_decoding() -> None:
    """Test refresh token issuance and claims parsing."""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    token, jti, expire = TokenService.create_refresh_token(
        user_id=user_id,
        token_version=1,
    )

    payload = TokenService.decode_token(token, expected_type="refresh")
    assert payload["sub"] == user_id
    assert payload["jti"] == jti
    assert payload["type"] == "refresh"


def test_invalid_token_type() -> None:
    """Test token type mismatch raises AuthenticationException."""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    access_token = TokenService.create_access_token(
        user_id=user_id,
        username="testuser",
        email="testuser@example.com",
        token_version=1,
        roles=["User"],
        permissions=[],
    )

    with pytest.raises(AuthenticationException):
        TokenService.decode_token(access_token, expected_type="refresh")
