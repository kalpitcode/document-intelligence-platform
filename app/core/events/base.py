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
