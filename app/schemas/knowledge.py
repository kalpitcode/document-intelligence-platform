"""
Knowledge Engine & Search Schemas Module
=========================================

Pydantic V2 data models for semantic, keyword, and hybrid search requests, results,
search history audit, embedding models, and re-indexing endpoints.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Strict Pydantic V2 validation on input search parameters and metadata filters.
- Enterprise OpenAPI documentation examples and schema definitions.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, FieldValidationInfo, field_validator


class QueryTypeEnum(str, Enum):
    """Supported search strategy modes."""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class SearchFilterSchema(BaseModel):
    """Metadata payload filter options for search queries."""
    model_config = ConfigDict(extra="ignore")

    document_id: str | None = Field(default=None, description="Filter by specific Document ID")
    mime_type: str | None = Field(default=None, description="Filter by document MIME type (e.g. application/pdf)")
    language: str | None = Field(default=None, description="Filter by ISO language code (e.g. en)")
    visibility: str | None = Field(default=None, description="Filter by document visibility (private, public)")
    tags: list[str] | None = Field(default=None, description="Filter by document tags")


class SearchRequest(BaseModel):
    """Request payload for executing semantic, keyword, or hybrid search."""
    model_config = ConfigDict(extra="ignore")

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        example="Q3 financial report revenue margin analysis",
        description="Search query string",
    )
    query_type: QueryTypeEnum = Field(
        default=QueryTypeEnum.HYBRID,
        description="Search strategy: 'semantic', 'keyword', or 'hybrid'",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of top results to return",
    )
    score_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum score threshold cut-off",
    )
    filters: SearchFilterSchema | None = Field(
        default=None,
        description="Metadata filters enforcing date, document, language, or file type criteria",
    )


class SearchResultItem(BaseModel):
    """Single matching document chunk result item."""
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str = Field(..., description="Unique ID of matching chunk")
    document_id: str = Field(..., description="Parent Document ID")
    owner_id: str | None = Field(default=None, description="Document Owner User ID")
    score: float = Field(..., description="Normalized match score [0.0 - 1.0]")
    page_number: int | None = Field(default=1, description="Page number where chunk appears")
    chunk_index: int | None = Field(default=0, description="Sequential chunk index")
    snippet: str = Field(..., description="Clean text snippet preview")
    highlighted_text: str = Field(..., description="HTML/Marked highlighted query term snippet")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Document metadata properties")

    @field_validator("page_number", mode="before")
    @classmethod
    def sanitize_page_number(cls, v: Any) -> int:
        if v is None:
            return 1
        try:
            return int(v)
        except (ValueError, TypeError):
            return 1

    @field_validator("chunk_index", mode="before")
    @classmethod
    def sanitize_chunk_index(cls, v: Any) -> int:
        if v is None:
            return 0
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0


class SearchResponse(BaseModel):
    """Response payload returned by Search API."""
    model_config = ConfigDict(from_attributes=True)

    query: str = Field(..., description="Original search query")
    query_type: str = Field(..., description="Executed search strategy")
    total_results: int = Field(..., description="Number of results returned")
    latency_ms: int = Field(..., description="Execution latency in milliseconds")
    results: list[SearchResultItem] = Field(default_factory=list, description="Ordered list of candidate results")


class SearchHistoryItemResponse(BaseModel):
    """Single user search history audit item."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Search history audit record ID")
    query: str = Field(..., description="Query string")
    query_type: str = Field(..., description="Query strategy")
    result_count: int = Field(..., description="Number of results returned")
    latency_ms: int = Field(..., description="Query latency in ms")
    created_at: datetime = Field(..., description="Search execution timestamp")


class SearchHistoryListResponse(BaseModel):
    """Paginated user search history list response."""
    model_config = ConfigDict(from_attributes=True)

    items: list[SearchHistoryItemResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total history count")


class EmbeddingModelResponse(BaseModel):
    """Registered embedding model metadata schema."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Model record ID")
    name: str = Field(..., description="Model name / path")
    dimension: int = Field(..., description="Embedding vector output dimension")
    provider: str = Field(..., description="Framework / provider")
    version: str = Field(..., description="Model version")
    is_active: bool = Field(..., description="Active flag")


class ReindexRequest(BaseModel):
    """Payload for requesting document re-indexing into vector database."""
    model_config = ConfigDict(extra="ignore")

    document_id: str = Field(..., description="Document ID to re-index")


class ReindexResponse(BaseModel):
    """Response payload for document re-indexing request."""
    model_config = ConfigDict(from_attributes=True)

    document_id: str = Field(..., description="Target Document ID")
    message: str = Field(..., description="Re-indexing job status message")
    job_id: str | None = Field(default=None, description="Celery background job ID")
