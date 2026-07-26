"""
Permission Model Module
========================

Defines the fine-grained Permission database model.

**Architectural Rationale:**
- Permissions represent discrete actions on specific resources (e.g. `documents.read`).
- Separating resource and action allows programmatic authorization logic.
- Managed centrally for RBAC policies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.role import RoleModel


class PermissionModel(Base, UUIDMixin, TimestampMixin):
    """
    Permission entity in the database.

    Attributes:
        id: Primary key (UUID v4).
        name: Unique code (e.g. 'documents.read', 'users.write').
        description: Human readable explanation of what this permission permits.
        resource: Target resource (e.g. 'documents', 'users', 'admin').
        action: Permitted action (e.g. 'read', 'write', 'delete', 'full').
    """

    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Permission code, e.g. documents.read",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Description of what this permission enables",
    )
    resource: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Resource name (e.g., documents, users)",
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Action name (e.g., read, write, delete)",
    )

    # Many-to-many relationship with RoleModel
    roles: Mapped[list[RoleModel]] = relationship(
        "RoleModel",
        secondary="role_permissions",
        back_populates="permissions",
    )

    __table_args__ = (
        Index("ix_permissions_resource_action", "resource", "action"),
    )

    def __repr__(self) -> str:
        return f"<PermissionModel(id={self.id}, name='{self.name}')>"
