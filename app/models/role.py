"""
Role Model Module
==================

Defines the Role database model and role-permission association table.

**Architectural Rationale:**
- Roles group permissions into manageable security profiles (Admin, Manager, User, Viewer).
- Association table `role_permissions` forms a M2M relationship between Role and Permission.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.permission import PermissionModel
    from app.models.user import UserModel

# M2M Association Table between Role and Permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class RoleModel(Base, UUIDMixin, TimestampMixin):
    """
    Role entity in the database.

    Attributes:
        id: Primary key (UUID v4).
        name: Unique role name (e.g., Admin, Manager, User, Viewer).
        description: Description of the role responsibilities.
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique role identifier name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed description of the role",
    )

    # Relationships
    permissions: Mapped[list[PermissionModel]] = relationship(
        "PermissionModel",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )
    users: Mapped[list[UserModel]] = relationship(
        "UserModel",
        secondary="user_roles",
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<RoleModel(id={self.id}, name='{self.name}')>"
