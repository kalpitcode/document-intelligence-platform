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
    DocumentIndexed,
    DocumentProcessingCompleted,
    DocumentProcessingFailed,
    DocumentProcessingStarted,
    DocumentRemovedFromIndex,
    DocumentUploaded,
    DocumentVersionCreated,
    EmailVerificationRequested,
    EmbeddingCompleted,
    EmbeddingFailed,
    EmbeddingStarted,
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
    "DocumentIndexed",
    "DocumentProcessingCompleted",
    "DocumentProcessingFailed",
    "DocumentProcessingStarted",
    "DocumentRemovedFromIndex",
    "DocumentUploaded",
    "DocumentVersionCreated",
    "EmailVerificationRequested",
    "EmbeddingCompleted",
    "EmbeddingFailed",
    "EmbeddingStarted",
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
