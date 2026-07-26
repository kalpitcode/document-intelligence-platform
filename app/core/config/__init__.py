"""
Configuration Package
======================

Provides the `get_settings()` factory function — the single entry point
for configuration throughout the entire application.

**Architectural Rationale:**
- `@lru_cache` ensures settings are loaded once and reused (singleton).
- Environment detection happens here, not scattered across modules.
- Every module imports `get_settings` from this package — no direct
  instantiation of Settings classes anywhere else.

Usage::

    from app.core.config import get_settings

    settings = get_settings()
    print(settings.database_url)
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config.settings import Settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Factory function that returns the appropriate Settings instance
    based on the APP_ENV environment variable.

    Returns:
        Settings: The environment-specific configuration object.
    """
    from app.core.config.environments import (
        DevelopmentSettings,
        ProductionSettings,
        StagingSettings,
        TestingSettings,
    )

    env = os.getenv("APP_ENV", "development").lower()

    env_map: dict[str, type[Settings]] = {
        "development": DevelopmentSettings,
        "production": ProductionSettings,
        "testing": TestingSettings,
        "staging": StagingSettings,
    }

    settings_class = env_map.get(env, DevelopmentSettings)
    return settings_class()


__all__ = ["get_settings"]
