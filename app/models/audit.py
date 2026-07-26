"""
Audit Log Model Module
=======================

Defines the AuditLog database model.

**Architectural Rationale:**
- Comprehensive audit trail required for financial compliance and SOC 2 / ISO 27001 standards.
- Records all security events (login, logout, password changes, failed logins, role/permission grants).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import UserModel


class AuditLogModel(Base, UUIDMixin):
    """
    Security Audit Log entity.

    Attributes:
        id: Primary key (UUID v4).
        request_id: Distributed tracing request ID.
        user_id: User who performed the action (nullable for unauthenticated attempts).
        action: Standardized action code (e.g., 'USER_LOGIN', 'PASSWORD_CHANGE').
        target_resource: Resource acted upon (e.g. 'user:123', 'role:admin').
        status: Action status ('SUCCESS', 'FAILURE').
        ip_address: Client IP address.
        user_agent: HTTP User Agent string.
        timestamp: Action timestamp (UTC).
        details: Extra context as JSON dictionary.
    """

    __tablename__ = "audit_logs"

    request_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Tracing request ID",
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Associated user ID if authenticated",
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Security action identifier",
    )
    target_resource: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Target resource identifier",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="SUCCESS",
        index=True,
        doc="Outcome status: SUCCESS | FAILURE",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        doc="Originating IP address",
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="HTTP User-Agent string",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="UTC timestamp of audit event",
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        doc="Additional event metadata as JSON",
    )

    # Relationships
    user: Mapped[UserModel | None] = relationship(
        "UserModel",
        back_populates="audit_logs",
    )

    __table_args__ = (
        Index("ix_audit_logs_action_ts", "action", "timestamp"),
        Index("ix_audit_logs_user_ts", "user_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<AuditLogModel(id={self.id}, action='{self.action}', status='{self.status}')>"
