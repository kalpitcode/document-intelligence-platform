"""
Refresh Token Model Module
============================

Defines the RefreshToken database model.

**Architectural Rationale:**
- Refresh tokens are stored securely to support token rotation and remote revocation.
- Tracks device metadata, IP address, and revocation timestamp for security auditability.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import UserModel


class RefreshTokenModel(Base, UUIDMixin, TimestampMixin):
    """
    Refresh token persistence entity.

    Attributes:
        id: Primary key (UUID v4).
        user_id: Foreign key to User.
        jti: Unique JWT identifier (UUID string).
        device_name: Device identification.
        browser: Client browser details.
        operating_system: Client OS details.
        ip_address: Client IP address when token was issued.
        issued_at: Timestamp token was created.
        expires_at: Expiration timestamp.
        revoked_at: Revocation timestamp if invalidated.
        is_revoked: Boolean flag for revocation state.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner user ID",
    )
    jti: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique JWT JTI string identifier",
    )
    device_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Device name/type",
    )
    browser: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="User agent browser string",
    )
    operating_system: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="User agent OS string",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        doc="Originating IP address",
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Token issuance timestamp",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Token expiration timestamp",
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of manual or automatic revocation",
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Revocation status flag",
    )

    # Relationships
    user: Mapped[UserModel] = relationship(
        "UserModel",
        back_populates="refresh_tokens",
    )

    __table_args__ = (
        Index("ix_refresh_tokens_user_jti", "user_id", "jti"),
    )

    def __repr__(self) -> str:
        return f"<RefreshTokenModel(id={self.id}, user_id={self.user_id}, jti='{self.jti}')>"
