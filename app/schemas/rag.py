"""
RAG Chat Schemas Module
=======================

Pydantic validation schemas for the enterprise RAG Chat Engine.

Architectural Rationale:
- Input parameters bounds validation (temperature, max_tokens, top_k).
- OpenAPI documentation with examples and field descriptions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel, Field, ConfigDict


class RAGChatRequest(BaseModel):
    """Payload for submitting a RAG Chat query."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="User question to be answered using indexed enterprise documents.",
        examples=["What were BlackRock's key financial highlights in Q4?"],
    )
    session_id: uuid.UUID | None = Field(
        default=None,
        description="Optional existing chat session UUID. If omitted, a new chat session will be created.",
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Sampling temperature. Defaults to 0.0 for strict, deterministic factual responses.",
    )
    max_tokens: int = Field(
        default=1000,
        ge=1,
        le=4096,
        description="Maximum tokens allowed in the generated completion.",
    )
    search_mode: str = Field(
        default="hybrid",
        description="Search mode: 'hybrid', 'semantic', or 'keyword'.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of document chunks to retrieve.",
    )
    filters: dict[str, Any] | None = Field(
        default=None,
        description="Optional payload filters (e.g., mime_type, extension).",
    )


class CitationItem(BaseModel):
    """Citation metadata identifying the source document and chunk."""

    document_id: str = Field(..., description="Document UUID string.")
    document_name: str = Field(..., description="Original filename of the cited document.")
    page_number: int | None = Field(default=None, description="Page number where the cited text appears.")
    chunk_id: str = Field(..., description="Chunk UUID string.")
    snippet: str = Field(..., description="Extracted text snippet supporting the statement.")
    score: float = Field(..., description="Relevance score of the chunk.")


class RetrievedDocumentItem(BaseModel):
    """Summary of retrieved document sources."""

    document_id: str = Field(..., description="Document UUID string.")
    title: str = Field(..., description="Title or filename of the document.")
    page_number: int | None = Field(default=None, description="Page number of retrieved chunk.")
    score: float = Field(..., description="Relevance score.")


class TokenUsage(BaseModel):
    """Token consumption and cost telemetry."""

    prompt_tokens: int = Field(..., description="Tokens used in system & context prompt.")
    completion_tokens: int = Field(..., description="Tokens generated in response.")
    total_tokens: int = Field(..., description="Total tokens consumed.")
    cost: float = Field(..., description="Estimated cost in USD.")


class LatencyMetrics(BaseModel):
    """Detailed breakdown of end-to-end RAG pipeline latency."""

    prompt_build_time_ms: int = Field(..., description="Time spent formatting context and prompt in ms.")
    retrieval_time_ms: int = Field(..., description="Time spent performing hybrid vector search in ms.")
    generation_time_ms: int = Field(..., description="Time spent awaiting LLM response in ms.")
    total_latency_ms: int = Field(..., description="Total end-to-end request duration in ms.")


class RAGChatResponse(BaseModel):
    """Primary response envelope returned by RAG Chat endpoints."""

    session_id: uuid.UUID = Field(..., description="Chat session UUID.")
    message_id: uuid.UUID = Field(..., description="Unique message UUID for assistant answer.")
    answer: str = Field(..., description="Grounded, zero-hallucination assistant response.")
    citations: list[CitationItem] = Field(default_factory=list, description="Mandatory citations backing answer statements.")
    retrieved_documents: list[RetrievedDocumentItem] = Field(default_factory=list, description="Summary of retrieved source documents.")
    latency: LatencyMetrics = Field(..., description="Observability latency breakdowns.")
    token_usage: TokenUsage = Field(..., description="Token and cost metrics.")
    model: str = Field(..., description="LLM model used for completion.")


class ChatMessageResponse(BaseModel):
    """Schema representing an individual message within a conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    message: str
    citations: list[dict[str, Any]]
    token_count: int
    latency_ms: int
    created_at: datetime


class ChatSessionResponse(BaseModel):
    """Schema representing a chat session thread."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime


class ChatSessionDetailResponse(BaseModel):
    """Schema representing chat session details with full message history."""

    session: ChatSessionResponse
    messages: list[ChatMessageResponse]


class ChatSessionListResponse(BaseModel):
    """Paginated list of chat sessions."""

    items: list[ChatSessionResponse]
    total: int
    page: int
    size: int
