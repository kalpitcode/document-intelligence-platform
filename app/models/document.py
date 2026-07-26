"""
Document Storage Models Module
===============================

Defines database models for document management, versioning, metadata,
upload sessions, tags, and document-level permissions.

**Architectural Rationale:**
- Clean separation of core document record, versions, technical metadata, and ACLs.
- `SoftDeleteMixin` preserves document history for SOC 2 / financial compliance.
- PostgreSQL native JSON type with SQLite variant for metadata compatibility.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
import uuid
from typing import Any, TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.role import RoleModel
    from app.models.user import UserModel


class DocumentStatus(str, Enum):
    """Lifecycle status of a document."""
    PENDING = "Pending"
    UPLOADING = "Uploading"
    UPLOADED = "Uploaded"
    PROCESSING = "Processing"
    FAILED = "Failed"
    DELETED = "Deleted"
    ARCHIVED = "Archived"


class Visibility(str, Enum):
    """Access visibility level for a document."""
    PRIVATE = "Private"
    SHARED = "Shared"
    ORGANIZATION = "Organization"
    PUBLIC = "Public"


# Association table for Document <-> Tag Many-to-Many relationship
document_tags = Table(
    "document_tags",
    Base.metadata,
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class DocumentTagModel(Base, UUIDMixin, TimestampMixin):
    """Tag entity for indexing and categorizing documents."""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Tag name",
    )

    documents: Mapped[list[DocumentModel]] = relationship(
        "DocumentModel",
        secondary=document_tags,
        back_populates="tags",
    )

    def __repr__(self) -> str:
        return f"<DocumentTagModel(id={self.id}, name='{self.name}')>"


class DocumentModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Core Document Entity.

    Represents a managed file asset within the platform.
    """

    __tablename__ = "documents"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Owner user ID",
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Client original filename",
    )
    stored_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        doc="Server-side UUID filename",
    )
    storage_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc="Object storage path / bucket key",
    )
    mime_type: Mapped[str] = mapped_column(
        String(127),
        nullable=False,
        index=True,
        doc="Detected MIME type",
    )
    extension: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="File extension (e.g. .pdf)",
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="File size in bytes",
    )
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="SHA-256 content checksum",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="Latest version number",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DocumentStatus.UPLOADED.value,
        index=True,
        doc="Document lifecycle status",
    )
    visibility: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=Visibility.PRIVATE.value,
        index=True,
        doc="Document visibility level",
    )

    # Relationships
    owner: Mapped[UserModel] = relationship("UserModel", backref="documents")
    versions: Mapped[list[DocumentVersionModel]] = relationship(
        "DocumentVersionModel",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersionModel.version_number.desc()",
    )
    metadata_record: Mapped[DocumentMetadataModel | None] = relationship(
        "DocumentMetadataModel",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )
    tags: Mapped[list[DocumentTagModel]] = relationship(
        "DocumentTagModel",
        secondary=document_tags,
        back_populates="documents",
    )
    permissions: Mapped[list[DocumentPermissionModel]] = relationship(
        "DocumentPermissionModel",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_documents_owner_status", "owner_id", "status"),
        Index("ix_documents_sha256", "sha256_hash"),
    )

    def __repr__(self) -> str:
        return f"<DocumentModel(id={self.id}, filename='{self.original_filename}', status='{self.status}')>"


class DocumentVersionModel(Base, UUIDMixin):
    """Immutable historic version of a document file."""

    __tablename__ = "document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Parent document ID",
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Incremental version number",
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who uploaded this version",
    )
    storage_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc="Object storage path for this specific version",
    )
    checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 checksum of this version",
    )
    change_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional release notes or reason for version update",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="Version creation timestamp",
    )

    # Relationships
    document: Mapped[DocumentModel] = relationship("DocumentModel", back_populates="versions")

    def __repr__(self) -> str:
        return f"<DocumentVersionModel(id={self.id}, doc_id={self.document_id}, v={self.version_number})>"


class DocumentMetadataModel(Base, UUIDMixin, TimestampMixin):
    """Detailed technical and user-defined metadata for a document."""

    __tablename__ = "document_metadata"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="Associated document ID",
    )
    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Total page count (for PDFs/Docs)",
    )
    language: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        doc="Detected document language code",
    )
    file_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Categorized file type",
    )
    encoding: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        doc="Character encoding (e.g. utf-8)",
    )
    size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="File size in bytes",
    )
    custom_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        doc="Flexible user/system key-value metadata",
    )

    # Relationships
    document: Mapped[DocumentModel] = relationship("DocumentModel", back_populates="metadata_record")

    def __repr__(self) -> str:
        return f"<DocumentMetadataModel(id={self.id}, doc_id={self.document_id})>"


class UploadSessionModel(Base, UUIDMixin):
    """Tracks active and historical file upload sessions."""

    __tablename__ = "upload_sessions"

    upload_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="Client or system upload transaction ID",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User initiating upload",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="Session start timestamp",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Session completion timestamp",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="STARTED",
        doc="Session status: STARTED | UPLOADING | COMPLETED | FAILED",
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Percentage complete (0-100)",
    )

    def __repr__(self) -> str:
        return f"<UploadSessionModel(id={self.id}, upload_id='{self.upload_id}', status='{self.status}')>"


class DocumentPermissionModel(Base, UUIDMixin, TimestampMixin):
    """Document granular permission (ACL) entry."""

    __tablename__ = "document_permissions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    permission_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="READ",
        doc="Permission level: READ | WRITE | ADMIN",
    )

    # Relationships
    document: Mapped[DocumentModel] = relationship("DocumentModel", back_populates="permissions")

    def __repr__(self) -> str:
        return f"<DocumentPermissionModel(id={self.id}, doc_id={self.document_id}, level='{self.permission_level}')>"
