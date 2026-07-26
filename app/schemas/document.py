"""
Document API Schemas Module
============================

Pydantic V2 schemas for document request, response envelopes, versions, and metadata.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus, Visibility


class DocumentTagResponse(BaseModel):
    """Schema for document tag."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class DocumentVersionResponse(BaseModel):
    """Schema for document version record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    version_number: int
    uploaded_by: uuid.UUID | None = None
    storage_path: str
    checksum: str
    change_notes: str | None = None
    created_at: datetime


class DocumentMetadataResponse(BaseModel):
    """Schema for document metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    page_count: int | None = None
    language: str | None = None
    file_type: str | None = None
    encoding: str | None = None
    size: int
    custom_metadata: dict[str, Any] | None = None


class DocumentResponse(BaseModel):
    """Schema for full document entity response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    original_filename: str
    stored_filename: str
    storage_path: str
    mime_type: str
    extension: str
    file_size: int
    sha256_hash: str
    version: int
    status: DocumentStatus | str
    visibility: Visibility | str
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionResponse] = Field(default_factory=list)
    metadata_record: DocumentMetadataResponse | None = None
    tags: list[DocumentTagResponse] = Field(default_factory=list)


class DocumentUpdate(BaseModel):
    """Schema for updating document visibility or status."""

    visibility: Visibility | None = None
    status: DocumentStatus | None = None
    custom_metadata: dict[str, Any] | None = None


class UploadSessionResponse(BaseModel):
    """Schema for upload session state."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    upload_id: str
    user_id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None = None
    status: str
    progress: int


class DocumentDownloadResponse(BaseModel):
    """Schema for document download presigned URL response."""

    document_id: uuid.UUID
    original_filename: str
    download_url: str
    expires_in_seconds: int = 3600
