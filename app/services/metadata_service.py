"""
Document Metadata Service Module
=================================

Handles document metadata extraction, storage, and custom JSON field management.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.models.document import DocumentMetadataModel
from app.repositories.metadata_repository import MetadataRepository


class MetadataService:
    """Service managing document technical and custom metadata."""

    def __init__(self, metadata_repo: MetadataRepository) -> None:
        self.repo = metadata_repo

    async def create_metadata(
        self,
        document_id: uuid.UUID,
        file_size: int,
        file_type: str | None = None,
        language: str | None = "en",
        page_count: int | None = None,
        encoding: str | None = "utf-8",
        custom_metadata: dict[str, Any] | None = None,
    ) -> DocumentMetadataModel:
        """Create a metadata record for a newly uploaded document."""
        meta_data = {
            "document_id": document_id,
            "size": file_size,
            "file_type": file_type,
            "language": language,
            "page_count": page_count,
            "encoding": encoding,
            "custom_metadata": custom_metadata or {},
        }
        return await self.repo.create(**meta_data)

    async def get_by_document_id(
        self,
        document_id: uuid.UUID | str,
    ) -> DocumentMetadataModel | None:
        """Retrieve metadata record for a document."""
        return await self.repo.get_by_document_id(document_id)

    async def update_custom_metadata(
        self,
        document_id: uuid.UUID | str,
        custom_metadata: dict[str, Any],
    ) -> DocumentMetadataModel | None:
        """Update or merge custom JSON metadata for a document."""
        meta = await self.repo.get_by_document_id(document_id)
        if not meta:
            return None

        current = meta.custom_metadata or {}
        current.update(custom_metadata)

        return await self.repo.update(meta, custom_metadata=current)
