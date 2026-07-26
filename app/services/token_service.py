"""
Token Service Module
=====================

Provides JWT token issuance, claims encoding, verification, and revocation tracking.

**Architectural Rationale:**
- Access tokens are short-lived (e.g. 30m) carrying user identity, token version, roles, and permissions.
- Refresh tokens are long-lived (e.g. 7 days) carrying unique `jti` for rotation tracking.
- Blacklist checking integrates with Redis for instant token revocation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt

from app.core.config import get_settings
from app.core.exceptions.base import AuthenticationException, TokenExpiredException
from app.utils.time import utc_now


class TokenService:
    """
    Service for creating, decoding, and validating JWT access and refresh tokens.
    """

    @staticmethod
    def create_access_token(
        user_id: str | uuid.UUID,
        username: str,
        email: str,
        token_version: int,
        roles: list[str],
        permissions: list[str],
        expires_delta: timedelta | None = None,
    ) -> str:
        """
        Create a signed JWT access token.

        Claims:
            sub: User ID string
            username: User handle
            email: User email address
            token_version: Current token version for bulk revocation
            roles: List of assigned role names
            permissions: List of assigned permission codes
            jti: Unique token ID (UUID v4)
            iss: Token issuer
            aud: Token audience
            iat: Issued at timestamp
            exp: Expiration timestamp
            type: "access"
        """
        settings = get_settings()
        now = utc_now()

        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

        payload: dict[str, Any] = {
            "sub": str(user_id),
            "username": username,
            "email": email,
            "token_version": token_version,
            "roles": roles,
            "permissions": permissions,
            "jti": str(uuid.uuid4()),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "type": "access",
        }

        return jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    @staticmethod
    def create_refresh_token(
        user_id: str | uuid.UUID,
        token_version: int,
        expires_delta: timedelta | None = None,
    ) -> tuple[str, str, datetime]:
        """
        Create a signed JWT refresh token.

        Returns:
            Tuple of (encoded_jwt, jti_string, expiration_datetime).
        """
        settings = get_settings()
        now = utc_now()

        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(days=settings.jwt_refresh_token_expire_days)

        jti = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "token_version": token_version,
            "jti": jti,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "type": "refresh",
        }

        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        return token, jti, expire

    @staticmethod
    def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
        """
        Decode and validate a JWT token payload.

        Args:
            token: Encoded JWT string.
            expected_type: 'access' or 'refresh' (optional validation).

        Returns:
            Decoded payload dictionary.

        Raises:
            TokenExpiredException: If token has expired.
            AuthenticationException: If signature or claims are invalid.
        """
        settings = get_settings()

        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
                options={"verify_exp": True, "verify_iss": True, "verify_aud": True},
            )
        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredException(message="Token has expired") from e
        except jwt.PyJWTError as e:
            raise AuthenticationException(message=f"Invalid authentication token: {e!s}") from e

        if expected_type and payload.get("type") != expected_type:
            raise AuthenticationException(
                message=f"Invalid token type: expected '{expected_type}', got '{payload.get('type')}'"
            )

        return payload
