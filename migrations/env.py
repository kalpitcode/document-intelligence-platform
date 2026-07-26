"""
Alembic Environment Configuration
===================================

Configures Alembic to work with our async SQLAlchemy engine and
application settings.

**Architectural Rationale:**
- Database URL is loaded from application settings (not hardcoded in alembic.ini).
- `target_metadata` points to our `Base.metadata` so Alembic can
  auto-detect model changes for `--autogenerate` migrations.
- Supports both offline (SQL script) and online (direct connection) modes.
- Uses synchronous connection for migrations (Alembic doesn't support async).
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database.base import Base  # noqa: E402

# Alembic Config object
config = context.config

# Configure Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def get_database_url() -> str:
    """
    Get the synchronous database URL from application settings.

    Falls back to the alembic.ini value if settings can't be loaded.
    """
    try:
        from app.core.config import get_settings

        settings = get_settings()
        return settings.database_url_sync
    except Exception:
        # Fallback to alembic.ini or environment variable
        return os.getenv(
            "DATABASE_URL",
            config.get_main_option("sqlalchemy.url", ""),
        )


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    Useful for reviewing migrations before applying them.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Connects to the database and applies migrations directly.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
