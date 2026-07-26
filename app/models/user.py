"""
User Model Module
==================

Defines the User database model and user-role association table.

**Architectural Rationale:**
- Core identity representation for authentication & authorization.
- Uses UUID primary key and soft deletion via SoftDeleteMixin.
- Token versioning supports instantaneous token invalidation upon security events.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.audit import AuditLogModel
    from app.models.role import RoleModel
    from app.models.session import UserSessionModel
    from app.models.token import RefreshTokenModel

# M2M Association Table between User and Role
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class UserModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    User account entity in the database.

    Attributes:
        id: Primary key (UUID v4).
        email: Unique normalized email address.
        username: Unique username.
        hashed_password: Argon2id hashed password string.
        first_name: Given name.
        last_name: Family name.
        is_active: Whether user account is enabled.
        is_superuser: Administrative flag.
        email_verified: Whether email address has been verified.
        email_verified_at: Verification timestamp.
        last_login_at: Timestamp of last successful authentication.
        last_login_ip: IP address of last login.
        failed_login_attempts: Counter for failed login attempts.
        token_version: Integer incremented to invalidate all active JWTs.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Normalized user email address",
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique username identifier",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Argon2id password hash",
    )
    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="User first name",
    )
    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="User last name",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Flag indicating if the user account is active",
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Administrative superuser privilege flag",
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Verification status of the email address",
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of email verification",
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of most recent login",
    )
    last_login_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        doc="IP address used during most recent login",
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Failed authentication attempts counter",
    )
    token_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Token version counter for bulk JWT revocation",
    )

    # Relationships
    roles: Mapped[list[RoleModel]] = relationship(
        "RoleModel",
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )
    refresh_tokens: Mapped[list[RefreshTokenModel]] = relationship(
        "RefreshTokenModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list[UserSessionModel]] = relationship(
        "UserSessionModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list[AuditLogModel]] = relationship(
        "AuditLogModel",
        back_populates="user",
    )

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, email='{self.email}', username='{self.username}')>"
