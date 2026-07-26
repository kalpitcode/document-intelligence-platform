"""
Standard API Response Schemas
=============================

Defines the standard envelope schema for all API endpoints.

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {}
}
```
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


from datetime import datetime

from app.utils.time import utc_now


class APIResponse(BaseModel, Generic[T]):
    """Standardized API Response wrapper."""

    success: bool = Field(default=True, description="Success indicator flag")
    message: str = Field(default="Operation completed successfully", description="Human readable message")
    data: T | None = Field(default=None, description="Response payload")
    timestamp: datetime = Field(default_factory=utc_now, description="UTC timestamp of response")


# Alias for backward compatibility
BaseResponse = APIResponse


class StandardErrorDetail(BaseModel):
    """Standardized error details body."""

    code: str
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class APIErrorResponse(BaseModel):
    """Standardized API Error envelope."""

    success: bool = Field(default=False, description="Success indicator flag (False for errors)")
    message: str = Field(default="An error occurred", description="Human readable error message")
    error: StandardErrorDetail
