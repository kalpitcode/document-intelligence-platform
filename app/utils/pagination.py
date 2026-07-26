"""
Pagination Utilities Module
===========================

Provides reusable parameters and metadata builders for list endpoints.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    """Query parameter container for pagination."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate SQL OFFSET value."""
        return (self.page - 1) * self.page_size


class PageMetadata(BaseModel):
    """Pagination response metadata."""

    total_items: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedResult(BaseModel, Generic[T]):
    """Generic envelope for paginated datasets."""

    items: Sequence[T]
    metadata: PageMetadata

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        total: int,
        params: PageParams,
    ) -> PaginatedResult[T]:
        """Build PaginatedResult from items, count, and page params."""
        total_pages = math.ceil(total / params.page_size) if params.page_size > 0 else 0
        return cls(
            items=items,
            metadata=PageMetadata(
                total_items=total,
                page=params.page,
                page_size=params.page_size,
                total_pages=total_pages,
                has_next=params.page < total_pages,
                has_previous=params.page > 1,
            ),
        )
