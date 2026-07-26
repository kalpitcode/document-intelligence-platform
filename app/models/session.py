"""
User Session Model Module
==========================

Defines the UserSession database model.

**Architectural Rationale:**
- Tracks active sessions across devices, browsers, and IP addresses.
- Facilitates session list display, remote session termination, and auditability.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import UserModel


class UserSessionModel(Base, UUIDMixin, TimestampMixin):
    """
    User session entity.

    Attributes:
        id: Primary key (UUID v4).
        user_id: Foreign key to User.
        device: Client device representation.
        browser: Client browser string.
        ip: Client IP address.
        login_time: Timestamp of session start.
        last_activity: Timestamp of most recent request.
        logout_time: Timestamp of session end (if logged out).
    """

    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User owner of the session",
    )
    device: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Client device info",
    )
    browser: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Client browser info",
    )
    ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        doc="Client IP address",
    )
    login_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Session creation timestamp",
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Last recorded activity timestamp",
    )
    logout_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Session termination timestamp",
    )

    # Relationships
    user: Mapped[UserModel] = relationship(
        "UserModel",
        back_populates="sessions",
    )

    __table_args__ = (
        Index("ix_user_sessions_user_last_act", "user_id", "last_activity"),
    )

    def __repr__(self) -> str:
        return f"<UserSessionModel(id={self.id}, user_id={self.user_id}, ip='{self.ip}')>"
