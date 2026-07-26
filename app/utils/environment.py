"""
Environment Utility Module
============================

Provides helpers for runtime environment detection.

**Architectural Rationale:**
- Centralizes environment detection logic in one place.
- Prevents scattered `os.getenv()` calls throughout the codebase.
- All environment logic should use `get_settings()` when possible;
  these helpers are for low-level scenarios where settings aren't
  yet loaded (e.g., during settings construction).
"""

from __future__ import annotations

import os
import sys


def get_environment() -> str:
    """
    Get the current runtime environment.

    Returns:
        Environment name (development, production, testing, staging).
    """
    return os.getenv("APP_ENV", "development").lower()


def is_development() -> bool:
    """Check if running in development mode."""
    return get_environment() == "development"


def is_production() -> bool:
    """Check if running in production mode."""
    return get_environment() == "production"


def is_testing() -> bool:
    """Check if running in testing mode."""
    return get_environment() == "testing" or "pytest" in sys.modules


def is_docker() -> bool:
    """
    Check if the application is running inside a Docker container.

    Detects Docker by checking for the /.dockerenv file or
    cgroup indicators.
    """
    # Check for .dockerenv file
    if os.path.exists("/.dockerenv"):
        return True

    # Check cgroup (Linux)
    try:
        with open("/proc/1/cgroup") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        return False


def get_env_var(key: str, default: str = "") -> str:
    """
    Get an environment variable with a default value.

    Args:
        key: Environment variable name.
        default: Default value if not set.

    Returns:
        Environment variable value or default.
    """
    return os.getenv(key, default)


def require_env_var(key: str) -> str:
    """
    Get a required environment variable.

    Args:
        key: Environment variable name.

    Returns:
        Environment variable value.

    Raises:
        RuntimeError: If the environment variable is not set.
    """
    value = os.getenv(key)
    if value is None:
        msg = f"Required environment variable '{key}' is not set"
        raise RuntimeError(msg)
    return value
