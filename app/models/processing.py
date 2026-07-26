"""
Document Processing & OCR Database Models Module
==================================================

Defines database models for document content extraction, chunking, processing job tracking,
extracted tables, and extracted images.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- PostgreSQL native JSON type with SQLite variant for metadata/table payload compatibility.
- Eager/lazy relationship hooks connecting core Document entity with processing outputs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
import uuid
from typing import Any, TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.document import DocumentModel


class ProcessingStatus(str, Enum):
    """Lifecycle state of a document processing job."""
    QUEUED = "Queued"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    RETRYING = "Retrying"
    CANCELLED = "Cancelled"


class DocumentContentModel(Base, UUIDMixin, TimestampMixin):
    """
    Extracted Text & Metadata Content Entity.

    Stores normalized raw text, cleaned text, detected language, and content metrics.
    """

    __tablename__ = "document_contents"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="Associated Document ID",
    )
    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Unprocessed raw extracted text",
    )
    clean_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Normalized and sanitized clean text",
    )
    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
        index=True,
        doc="Detected ISO language code (e.g. en, es)",
    )
    character_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total character length of clean text",
    )
    word_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total word count",
    )
    page_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="Processed page count",
    )
    processing_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ProcessingStatus.QUEUED.value,
        index=True,
        doc="Processing status of content extraction",
    )

    # Relationships
    document: Mapped[DocumentModel] = relationship("DocumentModel", backref="content_record")

    def __repr__(self) -> str:
        return (
            f"<DocumentContentModel(id={self.id}, document_id={self.document_id}, "
            f"words={self.word_count}, language='{self.language}')>"
        )


class DocumentChunkModel(Base, UUIDMixin):
    """
    Sequential Text Chunk Entity.

    Represents a deterministic text chunk with character offsets, page mapping, and token estimate.
    """

    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Parent Document ID",
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="0-based sequential chunk index",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Chunk text payload",
    )
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Primary page number location for chunk",
    )
    start_offset: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Start character index in clean_text",
    )
    end_offset: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="End character index in clean_text",
    )
    token_estimate: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Estimated token count",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="Creation timestamp",
    )

    # Relationships
    document: Mapped[DocumentModel] = relationship("DocumentModel", backref="chunks")

    __table_args__ = (
        Index("ix_document_chunks_doc_seq", "document_id", "chunk_index", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentChunkModel(id={self.id}, document_id={self.document_id}, "
            f"index={self.chunk_index}, tokens={self.token_estimate})>"
        )


class ProcessingJobModel(Base, UUIDMixin, TimestampMixin):
    """
    Processing Job Execution Audit Entity.

    Tracks execution state, worker details, retry counts, duration, and errors.
    """

    __tablename__ = "processing_jobs"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target Document ID",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ProcessingStatus.QUEUED.value,
        index=True,
        doc="Current job status",
    )
    worker_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="celery.default_worker",
        doc="Name/hostname of processing worker",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Processing start timestamp",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Processing completion timestamp",
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Execution duration in milliseconds",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Exception message if failed",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of job retries",
    )

    # Relationships
    document: Mapped[DocumentModel] = relationship("DocumentModel", backref="processing_jobs")

    def __repr__(self) -> str:
        return f"<ProcessingJobModel(id={self.id}, document_id={self.document_id}, status='{self.status}')>"


class ExtractedTableModel(Base, UUIDMixin):
    """
    Extracted PDF/Doc Table Payload Entity.

    Stores tabular data in structured JSON format with page location.
    """

    __tablename__ = "extracted_tables"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Parent Document ID",
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="1-based page number where table appears",
    )
    table_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="0-based table index on page",
    )
    table_json: Mapped[dict[str, Any] | list[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        doc="Structured table rows and columns JSON payload",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="Creation timestamp",
    )

    # Relationships
    document: Mapped[DocumentModel] = relationship("DocumentModel", backref="tables")

    def __repr__(self) -> str:
        return (
            f"<ExtractedTableModel(id={self.id}, document_id={self.document_id}, "
            f"page={self.page_number}, table_idx={self.table_index})>"
        )


class ExtractedImageModel(Base, UUIDMixin):
    """
    Extracted Embedded Image Metadata Entity.

    Tracks extracted embedded figures/photos stored in object storage.
    """

    __tablename__ = "extracted_images"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Parent Document ID",
    )
    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="1-based page number location",
    )
    storage_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc="Object storage path / bucket key",
    )
    width: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Image width in pixels",
    )
    height: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Image height in pixels",
    )
    format: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="Image format (png, jpeg, webp)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="Creation timestamp",
    )

    # Relationships
    document: Mapped[DocumentModel] = relationship("DocumentModel", backref="extracted_images")

    def __repr__(self) -> str:
        return (
            f"<ExtractedImageModel(id={self.id}, document_id={self.document_id}, "
            f"page={self.page_number}, format='{self.format}')>"
        )
