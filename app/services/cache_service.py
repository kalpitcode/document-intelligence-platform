"""
Cache Service Module
=====================

Provides high-level Redis operations for authentication security:
- Token revocation blacklist
- Account lockout counter & decay
- Email verification & password reset temporary tokens

**Architectural Rationale:**
- Abstracts raw Redis key formatting and TTL management.
- Handles Redis unavailability gracefully with local fallback during unit testing.
"""

from __future__ import annotations

import logging

from app.core.cache.redis import redis_manager
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Fallback in-memory dict for environments where Redis is not running or during unit tests
_in_memory_store: dict[str, str] = {}


class CacheService:
    """
    High-level Redis cache helper for IAM operations.
    """

    @staticmethod
    async def blacklist_token(jti: str, ttl_seconds: int) -> None:
        """
        Add a JWT JTI to the revocation blacklist until its expiration.

        Args:
            jti: Unique JWT ID.
            ttl_seconds: Remaining validity duration in seconds.
        """
        key = f"blacklist:jti:{jti}"
        try:
            client = redis_manager.get_client()
            await client.setex(key, ttl_seconds, "revoked")
        except Exception:
            _in_memory_store[key] = "revoked"

    @staticmethod
    async def is_token_blacklisted(jti: str) -> bool:
        """
        Check if a JWT JTI is blacklisted.

        Args:
            jti: Unique JWT ID.

        Returns:
            True if blacklisted, False otherwise.
        """
        key = f"blacklist:jti:{jti}"
        try:
            client = redis_manager.get_client()
            val = await client.get(key)
            return val is not None
        except Exception:
            return key in _in_memory_store

    @staticmethod
    async def record_failed_login(identifier: str) -> int:
        """
        Increment the failed login counter for an email/IP address.

        Args:
            identifier: Email address or IP address string.

        Returns:
            Updated failure count.
        """
        settings = get_settings()
        key = f"lockout:failed:{identifier}"
        ttl = settings.account_lockout_minutes * 60

        try:
            client = redis_manager.get_client()
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, ttl)
            return count
        except Exception:
            curr = int(_in_memory_store.get(key, 0)) + 1
            _in_memory_store[key] = str(curr)
            return curr

    @staticmethod
    async def is_account_locked(identifier: str) -> bool:
        """
        Check if an account or IP address is currently locked out.

        Args:
            identifier: Email address or IP address string.

        Returns:
            True if account is locked out.
        """
        settings = get_settings()
        key = f"lockout:failed:{identifier}"

        try:
            client = redis_manager.get_client()
            val = await client.get(key)
            if val is not None and int(val) >= settings.max_failed_login_attempts:
                return True
            return False
        except Exception:
            val = _in_memory_store.get(key)
            return val is not None and int(val) >= settings.max_failed_login_attempts

    @staticmethod
    async def clear_failed_logins(identifier: str) -> None:
        """
        Reset the failed login attempt counter upon successful login.

        Args:
            identifier: Email address or IP address string.
        """
        key = f"lockout:failed:{identifier}"
        try:
            client = redis_manager.get_client()
            await client.delete(key)
        except Exception:
            _in_memory_store.pop(key, None)

    @staticmethod
    async def store_temporary_token(
        token_type: str,
        token: str,
        value: str,
        ttl_seconds: int = 3600,
    ) -> None:
        """
        Store temporary tokens (e.g. password reset, email verification).

        Args:
            token_type: 'password_reset' or 'email_verify'
            token: Secret random token string
            value: Associated data (e.g., user_id or email)
            ttl_seconds: Token TTL in seconds (default 1 hour)
        """
        key = f"token:{token_type}:{token}"
        try:
            client = redis_manager.get_client()
            await client.setex(key, ttl_seconds, value)
        except Exception:
            _in_memory_store[key] = value

    @staticmethod
    async def get_temporary_token_value(token_type: str, token: str) -> str | None:
        """
        Retrieve data associated with a temporary token.

        Args:
            token_type: 'password_reset' or 'email_verify'
            token: Secret token string

        Returns:
            Stored value string or None if expired/not found.
        """
        key = f"token:{token_type}:{token}"
        try:
            client = redis_manager.get_client()
            return await client.get(key)
        except Exception:
            return _in_memory_store.get(key)

    @staticmethod
    async def delete_temporary_token(token_type: str, token: str) -> None:
        """
        Invalidate a temporary token after single use.
        """
        key = f"token:{token_type}:{token}"
        try:
            client = redis_manager.get_client()
            await client.delete(key)
        except Exception:
            _in_memory_store.pop(key, None)
