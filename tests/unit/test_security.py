"""
Security & Logging Unit Tests
=============================
"""

from __future__ import annotations

import logging
import pytest

from app.core.logging.formatters import JSONFormatter, redact_sensitive_data
from app.middlewares.rate_limit import SlidingWindowRateLimiter
from app.middlewares.security import validate_environment_and_secrets


def test_secret_redacting() -> None:
    data = {
        "username": "admin",
        "password": "super_secret_pass",
        "nested": {"api_key": "sk_test_12345"},
    }
    cleaned = redact_sensitive_data(data)
    assert cleaned["username"] == "admin"
    assert cleaned["password"] == "******[REDACTED]******"
    assert cleaned["nested"]["api_key"] == "******[REDACTED]******"


def test_json_formatter_observability_fields() -> None:
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="User authenticated",
        args=(),
        exc_info=None,
    )
    setattr(record, "user_id", "user-123")
    formatted = formatter.format(record)
    assert '"level":"INFO"' in formatted
    assert '"user_id":"user-123"' in formatted
    assert '"trace_id"' in formatted


def test_rate_limiter_sliding_window() -> None:
    limiter = SlidingWindowRateLimiter(limit=2, window_sec=60)
    key = "test_client_1"

    allowed1, rem1, _ = limiter.is_allowed(key)
    assert allowed1 is True
    assert rem1 == 1

    allowed2, rem2, _ = limiter.is_allowed(key)
    assert allowed2 is True
    assert rem2 == 0

    allowed3, _, reset_sec = limiter.is_allowed(key)
    assert allowed3 is False
    assert reset_sec > 0


def test_environment_and_secrets_validator() -> None:
    res = validate_environment_and_secrets()
    assert "status" in res
    assert "environment" in res
