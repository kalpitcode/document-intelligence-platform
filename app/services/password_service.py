"""
Password Service Module
========================

Provides production-grade password hashing, verification, and complexity validation.

**Architectural Rationale:**
- Uses Argon2id (the winner of the Password Hashing Competition and OWASP recommended algorithm).
- Never stores plaintext passwords.
- Enforces strict password complexity rules (length, uppercase, lowercase, numbers, special characters).
- Provides constant-time byte string comparisons via `hmac.compare_digest`.
"""

from __future__ import annotations

import hmac
import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.core.exceptions.base import ValidationException

# Initialize Argon2id PasswordHasher with production defaults (time_cost=3, memory_cost=65536 = 64MB, parallelism=4)
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


class PasswordService:
    """
    Password security service for hashing, verification, and policy enforcement.
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plaintext password using Argon2id.

        Args:
            password: Plaintext password.

        Returns:
            Argon2id encoded hash string.
        """
        return _hasher.hash(password)

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify a plaintext password against an Argon2id hash.

        Args:
            password: Plaintext password.
            hashed_password: Stored Argon2id hash string.

        Returns:
            True if password matches hash, False otherwise.
        """
        try:
            return _hasher.verify(hashed_password, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    @staticmethod
    def needs_rehash(hashed_password: str) -> bool:
        """
        Check if an existing password hash needs to be rehashed to meet updated security parameters.

        Args:
            hashed_password: Stored Argon2id hash string.

        Returns:
            True if rehash required, False otherwise.
        """
        try:
            return _hasher.check_needs_rehash(hashed_password)
        except InvalidHashError:
            return True

    @staticmethod
    def validate_password_complexity(password: str) -> None:
        """
        Validate plaintext password against security policy rules:
        - Minimum length (configurable, default 12)
        - Must contain at least 1 uppercase letter
        - Must contain at least 1 lowercase letter
        - Must contain at least 1 digit
        - Must contain at least 1 special character (@$!%*?&#^()_-+=)

        Raises:
            ValidationException: If any complexity requirement is violated.
        """
        settings = get_settings()
        min_len = settings.password_min_length

        errors = []
        if len(password) < min_len:
            errors.append(f"Password must be at least {min_len} characters long.")

        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter.")

        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter.")

        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit.")

        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
            errors.append("Password must contain at least one special character.")

        if errors:
            raise ValidationException(
                message="Password complexity validation failed",
                errors=[{"field": "password", "message": err, "type": "complexity"} for err in errors],
            )

    @staticmethod
    def constant_time_compare(val1: str, val2: str) -> bool:
        """
        Perform constant-time comparison of two strings to prevent timing attacks.

        Args:
            val1: First string.
            val2: Second string.

        Returns:
            True if strings are identical.
        """
        return hmac.compare_digest(val1.encode("utf-8"), val2.encode("utf-8"))
