"""
Unit Tests for PasswordService
================================
"""

from __future__ import annotations

import pytest

from app.core.exceptions.base import ValidationException
from app.services.password_service import PasswordService


def test_password_hash_and_verification() -> None:
    """Test Argon2id hashing and password verification."""
    password = "SecurePassword123!"
    hashed = PasswordService.hash_password(password)

    assert hashed.startswith("$argon2id$")
    assert PasswordService.verify_password(password, hashed) is True
    assert PasswordService.verify_password("WrongPassword123!", hashed) is False


def test_password_complexity_success() -> None:
    """Test valid complex password."""
    valid_password = "SuperStrongPassword123!"
    PasswordService.validate_password_complexity(valid_password)


def test_password_complexity_failure() -> None:
    """Test password complexity rules rejection."""
    invalid_passwords = [
        "short1!",  # too short
        "alllowercase123!",  # no uppercase
        "ALLUPPERCASE123!",  # no lowercase
        "NoDigitsHere!",  # no digit
        "NoSpecialChar123",  # no special char
    ]

    for p in invalid_passwords:
        with pytest.raises(ValidationException):
            PasswordService.validate_password_complexity(p)


def test_constant_time_compare() -> None:
    """Test constant time string comparison."""
    assert PasswordService.constant_time_compare("string1", "string1") is True
    assert PasswordService.constant_time_compare("string1", "string2") is False
