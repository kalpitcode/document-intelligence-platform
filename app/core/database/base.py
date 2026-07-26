"""
Database Base Module
=====================

Defines the SQLAlchemy declarative base and reusable mixins for all models.

**Architectural Rationale:**
- A single `Base` class ensures all models share the same metadata registry.
- Mixins (`UUIDMixin`, `TimestampMixin`) enforce consistent patterns:
  every table gets a UUID primary key and audit timestamps.
- Using `mapped_column` and `Mapped` types (SQLAlchemy 2.0 style) provides
  full type safety integrated with mypy.
- The base is imported by `migrations/env.py` so Alembic can auto-detect
  model changes.

**Connection to the system:**
- All future models inherit from `Base`.
- `migrations/env.py` imports `Base.metadata` for autogenerate.
- `app.core.database.session` uses `Base` for engine/session setup.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Naming convention for constraints — Alembic needs these for
# deterministic migration names and to support auto-generated
# index/constraint names without conflicts.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy models.

    All models MUST inherit from this class. It provides:
    - Shared metadata with constraint naming conventions.
    - Type-safe column declarations via `Mapped` and `mapped_column`.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def to_dict(self) -> dict[str, Any]:
        """Serialize model instance to a dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """Generate a developer-friendly string representation."""
        class_name = type(self).__name__
        attrs = ", ".join(
            f"{col.name}={getattr(self, col.name)!r}"
            for col in self.__table__.columns
            if col.primary_key
        )
        return f"<{class_name}({attrs})>"


class UUIDMixin:
    """
    Mixin that adds a UUID primary key column.

    Uses PostgreSQL's native UUID type with server-side default
    for maximum compatibility and performance.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        nullable=False,
        comment="Unique identifier (UUID v4)",
    )


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamp columns.

    - `created_at` is set once when the row is inserted.
    - `updated_at` is automatically updated on every modification.
    - All timestamps are UTC to avoid timezone ambiguity.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("now()"),
        nullable=False,
        comment="Timestamp when the record was created (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        comment="Timestamp when the record was last updated (UTC)",
    )


class SoftDeleteMixin:
    """
    Mixin for soft-delete support.

    Instead of physically deleting rows, sets `deleted_at` timestamp.
    Queries should filter on `deleted_at IS NULL` by default.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        comment="Soft delete timestamp (NULL = active)",
    )

    @property
    def is_deleted(self) -> bool:
        """Check whether this record has been soft-deleted."""
        return self.deleted_at is not None
