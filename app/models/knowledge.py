"""
Enterprise AI Knowledge & Vector Search Database Models Module
===============================================================

Defines database models for vector embedding jobs, user search history execution audits,
and embedding model registries.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Tracks granular background job status for chunk embedding workers.
- Records user search query history with latency and parameter diagnostics for audit & analytics.
- Maintains registry of active embedding models and vector dimensions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.document import DocumentModel
    from app.models.user import UserModel


class EmbeddingJobStatus(str, Enum):
    """Lifecycle state of an embedding generation job."""
    QUEUED = "Queued"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    RETRYING = "Retrying"


class EmbeddingJobModel(Base, UUIDMixin, TimestampMixin):
    """
    Embedding Job Execution Audit Entity.

    Tracks chunk vector embedding generation job state, execution duration, and errors.
    """

    __tablename__ = "embedding_jobs"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target Document ID",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=EmbeddingJobStatus.QUEUED.value,
        index=True,
        doc="Current job execution status",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Job start timestamp",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Job completion timestamp",
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Execution duration in milliseconds",
    )
    embedding_model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="sentence-transformers/all-MiniLM-L6-v2",
        doc="Embedding model identifier used",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Failure exception message if job failed",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of job retries executed",
    )

    # Relationships
    document: Mapped[DocumentModel] = relationship("DocumentModel", backref="embedding_jobs")

    def __repr__(self) -> str:
        return f"<EmbeddingJobModel(id={self.id}, document_id={self.document_id}, status='{self.status}')>"


class SearchHistoryModel(Base, UUIDMixin):
    """
    User Search Execution Audit Entity.

    Records user search queries, query type, match count, and execution latency.
    """

    __tablename__ = "search_histories"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User ID who performed search",
    )
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Search query text",
    )
    query_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="hybrid",
        index=True,
        doc="Type of search executed (semantic, keyword, hybrid)",
    )
    result_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of matching results returned",
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total query latency in milliseconds",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
        doc="Search timestamp",
    )

    # Relationships
    user: Mapped[UserModel] = relationship("UserModel", backref="search_history")

    def __repr__(self) -> str:
        return (
            f"<SearchHistoryModel(id={self.id}, user_id={self.user_id}, "
            f"type='{self.query_type}', results={self.result_count})>"
        )


class EmbeddingModelModel(Base, UUIDMixin, TimestampMixin):
    """
    Embedding Model Registry Entity.

    Defines registered embedding model specifications, dimensions, and active status.
    """

    __tablename__ = "embedding_models"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="Embedding model name / HF path",
    )
    dimension: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=384,
        doc="Vector embedding output dimension",
    )
    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="sentence-transformers",
        doc="Provider framework (e.g., sentence-transformers, openai, onnx)",
    )
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="v1.0",
        doc="Model version string",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        doc="Whether this model is enabled for generation & vector indexing",
    )

    def __repr__(self) -> str:
        return (
            f"<EmbeddingModelModel(id={self.id}, name='{self.name}', "
            f"dim={self.dimension}, active={self.is_active})>"
        )
