"""
Environment-Specific Configuration
====================================

Subclasses of the base Settings that override defaults for each environment.

**Architectural Rationale:**
- Each environment (dev, prod, test) has its own class with sensible defaults.
- This avoids scattering environment-specific logic throughout the codebase.
- The factory in `__init__.py` selects the correct class based on APP_ENV.
- Production settings disable debug, increase pool sizes, and use JSON logging.

**Connection to the system:**
- Used by `get_settings()` in `__init__.py` to instantiate the right config.
"""

from __future__ import annotations

from app.core.config.settings import Settings


class DevelopmentSettings(Settings):
    """Development environment — verbose logging, debug enabled."""

    app_debug: bool = True
    app_workers: int = 1
    log_level: str = "DEBUG"
    log_format: str = "console"
    postgres_echo: bool = True


class ProductionSettings(Settings):
    """Production environment — optimized for performance and security."""

    app_debug: bool = False
    app_workers: int = 4
    log_level: str = "WARNING"
    log_format: str = "json"
    postgres_echo: bool = False
    postgres_pool_size: int = 30
    postgres_max_overflow: int = 20


class TestingSettings(Settings):
    """Testing environment — isolated, deterministic configuration."""

    app_env: str = "testing"
    app_debug: bool = True
    app_workers: int = 1
    log_level: str = "DEBUG"
    log_format: str = "console"
    postgres_db: str = "document_intelligence_test"
    postgres_echo: bool = False
    redis_db: int = 15  # Separate Redis DB for tests


class StagingSettings(Settings):
    """Staging environment — mirrors production with additional logging."""

    app_debug: bool = False
    app_workers: int = 2
    log_level: str = "INFO"
    log_format: str = "json"
    postgres_echo: bool = False
