"""
Base Response Schemas
======================

Pydantic V2 models for standardized API response envelopes.

**Architectural Rationale:**
- Every API response follows a consistent envelope structure.
- `BaseResponse` provides `success`, `message`, and `data` fields.
- `ErrorResponse` standardizes error reporting.
- Using `model_config` with `from_attributes=True` enables ORM
  model → schema conversion for future model endpoints.

**Connection to the system:**
- All API endpoint return types inherit from these base schemas.
- Exception handlers use `ErrorResponse` for error formatting.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """
    Standard API response envelope.

    All successful API responses MUST use this structure.
    """

    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(default=True, description="Whether the request was successful")
    message: str = Field(default="Success", description="Human-readable response message")
    data: T | None = Field(default=None, description="Response payload")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Response timestamp (UTC)",
    )


class ErrorDetail(BaseModel):
    """Structured error detail within an error response."""

    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    request_id: str | None = Field(default=None, description="Request ID for tracing")
    detail: dict[str, Any] = Field(default_factory=dict, description="Additional error context")
    errors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Validation errors (if applicable)",
    )


class ErrorResponse(BaseModel):
    """Standard API error response envelope."""

    success: bool = Field(default=False)
    error: ErrorDetail = Field(description="Error details")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Response timestamp (UTC)",
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response envelope for list endpoints.

    Provides cursor-based or offset-based pagination metadata.
    """

    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(default=True)
    message: str = Field(default="Success")
    data: list[T] = Field(default_factory=list, description="Page of results")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Response timestamp (UTC)",
    )
