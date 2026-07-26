"""
Base Exception Module
======================

Defines the exception hierarchy for the entire application.

**Architectural Rationale:**
- A single base exception allows catch-all handling at the API boundary.
- Each infrastructure concern (DB, validation, external services) has its
  own exception type for precise error handling and monitoring/alerting.
- Exceptions carry structured data (code, status, detail) that maps directly
  to the API error response schema.
- Business logic raises domain exceptions; the global handler translates them
  to HTTP responses. This keeps HTTP concerns out of the service layer.

**Connection to the system:**
- Raised anywhere in the application (services, repositories, utilities).
- Caught by `app.core.exceptions.handlers` and translated to HTTP responses.
"""

from __future__ import annotations

from typing import Any


class BaseAppException(Exception):
    """
    Base exception for all application-specific errors.

    All custom exceptions MUST inherit from this class to ensure
    consistent error handling and response formatting.

    Attributes:
        message: Human-readable error message.
        error_code: Machine-readable error code for client-side handling.
        status_code: HTTP status code to return.
        detail: Additional context about the error.
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Serialize exception to a dictionary for API responses."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "detail": self.detail,
            }
        }


# ==============================================================================
# Validation Exceptions
# ==============================================================================


class ValidationException(BaseAppException):
    """
    Raised when input validation fails.

    Used for request body validation, query parameter validation,
    and business rule validation (e.g., "document size exceeds limit").
    """

    def __init__(
        self,
        message: str = "Validation error",
        detail: dict[str, Any] | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            detail=detail or {},
        )
        self.errors = errors or []

    def to_dict(self) -> dict[str, Any]:
        """Include validation errors in the response."""
        result = super().to_dict()
        if self.errors:
            result["error"]["errors"] = self.errors
        return result


# ==============================================================================
# Database Exceptions
# ==============================================================================


class DatabaseException(BaseAppException):
    """
    Raised when a database operation fails.

    Wraps SQLAlchemy errors with application-specific context.
    Never expose raw database errors to the client.
    """

    def __init__(
        self,
        message: str = "Database error",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=503,
            detail=detail or {},
        )


class EntityNotFoundException(BaseAppException):
    """
    Raised when a requested entity is not found in the database.
    """

    def __init__(
        self,
        entity_type: str = "Entity",
        entity_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        message = f"{entity_type} not found"
        if entity_id:
            message = f"{entity_type} with ID '{entity_id}' not found"
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404,
            detail=detail or {},
        )


# ==============================================================================
# Configuration Exceptions
# ==============================================================================


class ConfigurationException(BaseAppException):
    """
    Raised when the application configuration is invalid or missing.

    Typically raised during application startup if required environment
    variables are not set or have invalid values.
    """

    def __init__(
        self,
        message: str = "Configuration error",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            detail=detail or {},
        )


# ==============================================================================
# External Service Exceptions
# ==============================================================================


class ExternalServiceException(BaseAppException):
    """
    Raised when an external service call fails.

    Used for Redis, RabbitMQ, third-party API calls, etc.
    Includes the service name for monitoring and alerting.
    """

    def __init__(
        self,
        service_name: str = "external_service",
        message: str = "External service error",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            detail={"service": service_name, **(detail or {})},
        )
        self.service_name = service_name


# ==============================================================================
# Rate Limiting (future-proofing)
# ==============================================================================


class RateLimitException(BaseAppException):
    """Raised when a client exceeds the rate limit."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = 60,
    ) -> None:
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            detail={"retry_after_seconds": retry_after},
        )
        self.retry_after = retry_after


# ==============================================================================
# Authorization (future-proofing)
# ==============================================================================


class AuthenticationException(BaseAppException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication required",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            detail=detail or {},
        )


class AuthorizationException(BaseAppException):
    """Raised when the user lacks permission for an action."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            detail=detail or {},
        )
