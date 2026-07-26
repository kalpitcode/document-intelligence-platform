"""
Response Formatting Utilities
===============================

Provides standardized response builders for API endpoints.

**Architectural Rationale:**
- Ensures all API responses follow the same envelope structure.
- Route handlers call these builders instead of manually constructing
  response dictionaries — reducing duplication and inconsistency.
- Pagination helper computes metadata (total_pages, has_next, etc.)
  from raw query results.

**Connection to the system:**
- Used by route handlers in `app.api.v1.endpoints.*`.
- Returns schema instances from `app.schemas.base`.
"""

from __future__ import annotations

import math
from typing import Any, TypeVar

from app.schemas.base import BaseResponse, PaginatedResponse

T = TypeVar("T")


def success_response(
    data: Any = None,
    message: str = "Success",
) -> BaseResponse:
    """
    Build a successful API response.

    Args:
        data: Response payload.
        message: Human-readable message.

    Returns:
        BaseResponse with success=True.
    """
    return BaseResponse(
        success=True,
        message=message,
        data=data,
    )


def created_response(
    data: Any = None,
    message: str = "Created successfully",
) -> BaseResponse:
    """
    Build a response for resource creation (HTTP 201).

    Args:
        data: The created resource.
        message: Human-readable message.

    Returns:
        BaseResponse for 201 responses.
    """
    return BaseResponse(
        success=True,
        message=message,
        data=data,
    )


def paginated_response(
    data: list[Any],
    total: int,
    page: int,
    page_size: int,
    message: str = "Success",
) -> PaginatedResponse:
    """
    Build a paginated API response.

    Computes pagination metadata from the raw values.

    Args:
        data: List of items for the current page.
        total: Total number of items across all pages.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
        message: Human-readable message.

    Returns:
        PaginatedResponse with computed metadata.
    """
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    return PaginatedResponse(
        success=True,
        message=message,
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )
