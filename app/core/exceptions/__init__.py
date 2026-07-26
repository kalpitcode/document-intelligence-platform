"""
Exceptions Package
===================

Centralized exception definitions for the Document Intelligence Platform.

Usage::

    from app.core.exceptions import (
        BaseAppException,
        DatabaseException,
        EntityNotFoundException,
        ValidationException,
    )

    raise EntityNotFoundException(entity_type="Document", entity_id="abc-123")
"""

from __future__ import annotations

from app.core.exceptions.base import (
    AuthenticationException,
    AuthorizationException,
    BaseAppException,
    ConfigurationException,
    DatabaseException,
    EntityNotFoundException,
    ExternalServiceException,
    RateLimitException,
    ValidationException,
)
from app.core.exceptions.handlers import register_exception_handlers

__all__ = [
    "AuthenticationException",
    "AuthorizationException",
    "BaseAppException",
    "ConfigurationException",
    "DatabaseException",
    "EntityNotFoundException",
    "ExternalServiceException",
    "RateLimitException",
    "ValidationException",
    "register_exception_handlers",
]
