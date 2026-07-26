"""
Document Processing & OCR Schemas Module
=========================================

Pydantic V2 schemas for document content, chunks, processing jobs, tables, and images.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.processing import ProcessingStatus


class ProcessingJobResponse(BaseModel):
    """Schema representing processing job status."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    worker_name: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    error_message: str | None = None
    retry_count: int = 0
    created_at: datetime


class ProcessTriggerResponse(BaseModel):
    """Schema for processing invocation response."""
    job_id: uuid.UUID
    document_id: uuid.UUID
    status: str
    message: str


class DocumentContentResponse(BaseModel):
    """Schema for extracted document text & language metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    raw_text: str
    clean_text: str
    language: str
    character_count: int
    word_count: int
    page_count: int
    processing_status: str
    created_at: datetime
    updated_at: datetime


class DocumentChunkResponse(BaseModel):
    """Schema for sequential text chunk entity."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: int | None = None
    start_offset: int
    end_offset: int
    token_estimate: int
    created_at: datetime


class ExtractedTableResponse(BaseModel):
    """Schema for extracted document table."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    table_index: int
    table_json: dict[str, Any] | list[Any]
    created_at: datetime


class ExtractedImageResponse(BaseModel):
    """Schema for extracted embedded image metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    storage_path: str
    width: int
    height: int
    format: str
    download_url: str | None = None
    created_at: datetime
