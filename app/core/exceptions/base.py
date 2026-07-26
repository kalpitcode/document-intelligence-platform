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
        error_code: str = "AUTHENTICATION_ERROR",
        status_code: int = 401,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            detail=detail or {},
        )


class InvalidCredentialsException(AuthenticationException):
    """Raised when email or password is incorrect."""

    def __init__(
        self,
        message: str = "Invalid email or password",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTH_INVALID_CREDENTIALS",
            status_code=401,
            detail=detail or {},
        )


class AccountLockedException(AuthenticationException):
    """Raised when account is temporarily locked out."""

    def __init__(
        self,
        message: str = "Account is temporarily locked due to repeated failed login attempts",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTH_ACCOUNT_LOCKED",
            status_code=423,
            detail=detail or {},
        )


class TokenExpiredException(AuthenticationException):
    """Raised when access or refresh token has expired."""

    def __init__(
        self,
        message: str = "Token has expired",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTH_TOKEN_EXPIRED",
            status_code=401,
            detail=detail or {},
        )


class EmailNotVerifiedException(AuthenticationException):
    """Raised when unverified user attempts actions requiring verified email."""

    def __init__(
        self,
        message: str = "Email address has not been verified",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTH_EMAIL_NOT_VERIFIED",
            status_code=403,
            detail=detail or {},
        )


class AuthorizationException(BaseAppException):
    """Raised when the user lacks permission for an action."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        error_code: str = "AUTHORIZATION_ERROR",
        status_code: int = 403,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            detail=detail or {},
        )


class PermissionDeniedException(AuthorizationException):
    """Raised when required permission is missing."""

    def __init__(
        self,
        message: str = "Required permission is missing",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTH_PERMISSION_DENIED",
            status_code=403,
            detail=detail or {},
        )


class RoleRequiredException(AuthorizationException):
    """Raised when required role is missing."""

    def __init__(
        self,
        message: str = "Required role is missing",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTH_ROLE_REQUIRED",
            status_code=403,
            detail=detail or {},
        )


class ResourceForbiddenException(AuthorizationException):
    """Raised when ownership/resource access rule fails."""

    def __init__(
        self,
        message: str = "You do not have permission to access or modify this resource",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="AUTH_RESOURCE_FORBIDDEN",
            status_code=403,
            detail=detail or {},
        )


class NotFoundError(EntityNotFoundException):
    """Alias for EntityNotFoundException."""
    def __init__(self, message: str = "Resource not found", detail: dict[str, Any] | None = None) -> None:
        super().__init__(entity_type="Resource", detail=detail)
        self.message = message
        self.args = (message,)


class ForbiddenError(ResourceForbiddenException):
    """Alias for ResourceForbiddenException."""
    def __init__(self, message: str = "Forbidden", detail: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, detail=detail)


class ProcessingError(BaseAppException):
    """Raised when document processing pipeline fails."""
    def __init__(self, message: str = "Document processing failed", detail: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, error_code="PROCESSING_ERROR", status_code=500, detail=detail or {})


