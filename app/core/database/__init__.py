"""
Database Package
=================

Provides database engine, session management, and declarative base.

Usage::

    from app.core.database import Base, get_db_session, init_db, close_db
"""

from __future__ import annotations

from app.core.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.core.database.session import (
    check_db_health,
    close_db,
    get_db_session,
    get_engine,
    init_db,
)

__all__ = [
    "Base",
    "SoftDeleteMixin",
    "TimestampMixin",
    "UUIDMixin",
    "check_db_health",
    "close_db",
    "get_db_session",
    "get_engine",
    "init_db",
]
