"""
Domain Events Package
======================
"""

from __future__ import annotations

from app.core.events.base import (
    BaseDomainEvent,
    EmailVerificationRequested,
    EventBus,
    PasswordChanged,
    PermissionGranted,
    RoleAssigned,
    UserLoggedIn,
    UserRegistered,
)

__all__ = [
    "BaseDomainEvent",
    "EmailVerificationRequested",
    "EventBus",
    "PasswordChanged",
    "PermissionGranted",
    "RoleAssigned",
    "UserLoggedIn",
    "UserRegistered",
]
