"""
Domain Events Package
======================
"""

from __future__ import annotations

from app.core.events.base import (
    BaseDomainEvent,
    DocumentDeleted,
    DocumentDownloadRequested,
    DocumentUploaded,
    DocumentVersionCreated,
    EmailVerificationRequested,
    EventBus,
    PasswordChanged,
    PermissionGranted,
    RoleAssigned,
    UploadFailed,
    UserLoggedIn,
    UserRegistered,
)

__all__ = [
    "BaseDomainEvent",
    "DocumentDeleted",
    "DocumentDownloadRequested",
    "DocumentUploaded",
    "DocumentVersionCreated",
    "EmailVerificationRequested",
    "EventBus",
    "PasswordChanged",
    "PermissionGranted",
    "RoleAssigned",
    "UploadFailed",
    "UserLoggedIn",
    "UserRegistered",
]
