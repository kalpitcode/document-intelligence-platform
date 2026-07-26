"""
Domain Events Module
====================

Defines domain event classes and a lightweight synchronous/asynchronous EventBus abstraction.

**Architectural Rationale:**
- Domain events decouple core authentication logic from notification, logging, or background task dispatch.
- EventBus acts as a pub/sub mediator within the process boundary.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

from app.utils.time import utc_now


@dataclass(frozen=True)
class BaseDomainEvent:
    """Base class for all application domain events."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class UserRegistered(BaseDomainEvent):
    """Event emitted when a new user registers."""

    user_id: str = ""
    email: str = ""
    username: str = ""


@dataclass(frozen=True)
class UserLoggedIn(BaseDomainEvent):
    """Event emitted when a user successfully logs in."""

    user_id: str = ""
    email: str = ""
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class PasswordChanged(BaseDomainEvent):
    """Event emitted when a user updates their password."""

    user_id: str = ""
    email: str = ""


@dataclass(frozen=True)
class RoleAssigned(BaseDomainEvent):
    """Event emitted when a role is granted to a user."""

    user_id: str = ""
    role_name: str = ""
    assigned_by: str = ""


@dataclass(frozen=True)
class PermissionGranted(BaseDomainEvent):
    """Event emitted when a permission is linked to a role."""

    role_name: str = ""
    permission_name: str = ""


@dataclass(frozen=True)
class EmailVerificationRequested(BaseDomainEvent):
    """Event emitted when an email verification token is generated."""

    user_id: str = ""
    email: str = ""
    verification_token: str = ""


@dataclass(frozen=True)
class DocumentUploaded(BaseDomainEvent):
    """Event emitted when a new document is successfully uploaded."""

    document_id: str = ""
    owner_id: str = ""
    original_filename: str = ""
    file_size: int = 0
    sha256_hash: str = ""


@dataclass(frozen=True)
class DocumentDeleted(BaseDomainEvent):
    """Event emitted when a document is deleted."""

    document_id: str = ""
    deleted_by: str = ""
    reason: str = "user_action"


@dataclass(frozen=True)
class DocumentVersionCreated(BaseDomainEvent):
    """Event emitted when a new version of a document is created."""

    document_id: str = ""
    version_number: int = 1
    uploaded_by: str = ""
    checksum: str = ""


@dataclass(frozen=True)
class DocumentDownloadRequested(BaseDomainEvent):
    """Event emitted when a document download is initiated."""

    document_id: str = ""
    requested_by: str = ""
    ip_address: str | None = None


@dataclass(frozen=True)
class UploadFailed(BaseDomainEvent):
    """Event emitted when a document upload transaction fails."""

    upload_id: str = ""
    user_id: str = ""
    reason: str = ""


# --- Processing Domain Events ---

@dataclass(frozen=True)
class DocumentProcessingStarted(BaseDomainEvent):
    """Event emitted when document processing starts."""

    document_id: str = ""
    job_id: str = ""
    worker_name: str = ""


@dataclass(frozen=True)
class DocumentProcessingCompleted(BaseDomainEvent):
    """Event emitted when document processing completes successfully."""

    document_id: str = ""
    job_id: str = ""
    word_count: int = 0
    chunk_count: int = 0
    table_count: int = 0
    image_count: int = 0


@dataclass(frozen=True)
class DocumentProcessingFailed(BaseDomainEvent):
    """Event emitted when document processing encounters an error."""

    document_id: str = ""
    job_id: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class DocumentChunkCreated(BaseDomainEvent):
    """Event emitted when a document text chunk is generated."""

    document_id: str = ""
    chunk_id: str = ""
    chunk_index: int = 0
    token_estimate: int = 0


@dataclass(frozen=True)
class TableExtracted(BaseDomainEvent):
    """Event emitted when a table is extracted from a document page."""

    document_id: str = ""
    table_id: str = ""
    page_number: int = 1
    row_count: int = 0


@dataclass(frozen=True)
class ImageExtracted(BaseDomainEvent):
    """Event emitted when an embedded image is extracted from a document page."""

    document_id: str = ""
    image_id: str = ""
    page_number: int = 1
    storage_path: str = ""


EventType = TypeVar("EventType", bound=BaseDomainEvent)


class EventBus:
    """
    Lightweight in-memory domain event bus.
    """

    _subscribers: dict[type[BaseDomainEvent], list[Callable[[Any], None]]] = {}

    @classmethod
    def subscribe(cls, event_type: type[EventType], handler: Callable[[EventType], None]) -> None:
        """Register an event handler for a specific event type."""
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(handler)  # type: ignore[arg-type]

    @classmethod
    def publish(cls, event: BaseDomainEvent) -> None:
        """Publish a domain event to all registered subscribers."""
        event_type = type(event)
        handlers = cls._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass  # Event handlers must not crash the primary domain operation
