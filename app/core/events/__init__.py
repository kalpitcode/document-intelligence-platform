"""
Domain Events Package
======================
"""

from __future__ import annotations

from app.core.events.base import (
    BaseDomainEvent,
    DocumentChunkCreated,
    DocumentDeleted,
    DocumentDownloadRequested,
    DocumentProcessingCompleted,
    DocumentProcessingFailed,
    DocumentProcessingStarted,
    DocumentUploaded,
    DocumentVersionCreated,
    EmailVerificationRequested,
    EventBus,
    ImageExtracted,
    PasswordChanged,
    PermissionGranted,
    RoleAssigned,
    TableExtracted,
    UploadFailed,
    UserLoggedIn,
    UserRegistered,
)

__all__ = [
    "BaseDomainEvent",
    "DocumentChunkCreated",
    "DocumentDeleted",
    "DocumentDownloadRequested",
    "DocumentProcessingCompleted",
    "DocumentProcessingFailed",
    "DocumentProcessingStarted",
    "DocumentUploaded",
    "DocumentVersionCreated",
    "EmailVerificationRequested",
    "EventBus",
    "ImageExtracted",
    "PasswordChanged",
    "PermissionGranted",
    "RoleAssigned",
    "TableExtracted",
    "UploadFailed",
    "UserLoggedIn",
    "UserRegistered",
]
