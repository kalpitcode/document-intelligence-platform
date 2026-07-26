"""
AI Features ORM Data Models Module
===================================

SQLAlchemy ORM data models defining database storage for:
- `AIJobModel` (`ai_jobs`)
- `AIResultModel` (`ai_results`)
- `FeatureTemplateModel` (`feature_templates`)

Architectural Rationale:
- Implements Clean Architecture & SOLID design principles.
- Strict FK integrity linked to `UserModel` and `DocumentModel`.
- Cross-DB JSON column compatibility for PostgreSQL/SQLite.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database.base import Base

# Cross-DB JSON column support for SQLite and PostgreSQL
JSONColumn = JSON().with_variant(JSONB, "postgresql")


class AIJobStatus(str, Enum):
    """Execution status enum for AI jobs."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AIFeatureType(str, Enum):
    """Supported enterprise AI feature types."""

    SUMMARIZE = "summarize"
    CLASSIFY = "classify"
    EXTRACT = "extract"
    TRANSLATE = "translate"
    ANALYZE = "analyze"


class AIJobModel(Base):
    """
    AI Feature Execution Job ORM Model.

    Tracks execution state, retry counts, latency, and operational errors for AI tasks.
    """

    __tablename__ = "ai_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AIJobStatus.PENDING.value,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    model: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user: Mapped[Any] = relationship("UserModel", backref="ai_jobs")
    document: Mapped[Any] = relationship("DocumentModel", backref="ai_jobs")
    results: Mapped[list[AIResultModel]] = relationship(
        "AIResultModel",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_ai_jobs_user_doc", "user_id", "document_id"),
        Index("ix_ai_jobs_doc_feature", "document_id", "feature_type"),
    )


class AIResultModel(Base):
    """
    AI Feature Execution Result ORM Model.

    Stores structured output JSON payloads and metadata for document intelligence operations.
    """

    __tablename__ = "ai_results"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    result: Mapped[dict[str, Any]] = mapped_column(
        JSONColumn,
        nullable=False,
        default=dict,
    )
    result_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONColumn,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationships
    job: Mapped[AIJobModel | None] = relationship("AIJobModel", back_populates="results")
    document: Mapped[Any] = relationship("DocumentModel", backref="ai_results")

    __table_args__ = (
        Index("ix_ai_results_doc_feature", "document_id", "feature_type"),
    )


class FeatureTemplateModel(Base):
    """
    AI Feature System Prompt Template ORM Model.

    Version-controlled prompt template definitions for enterprise AI features.
    """

    __tablename__ = "feature_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    feature_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )
    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="1.0.0",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
