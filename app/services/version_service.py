"""
Document Version Service Module
=================================

Handles creation and history tracking of document file versions.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from app.models.document import DocumentVersionModel
from app.repositories.version_repository import VersionRepository


class VersionService:
    """Service managing document version control records."""

    def __init__(self, version_repo: VersionRepository) -> None:
        self.repo = version_repo

    async def create_version(
        self,
        document_id: uuid.UUID,
        version_number: int,
        storage_path: str,
        checksum: str,
        uploaded_by: uuid.UUID | None = None,
        change_notes: str | None = None,
    ) -> DocumentVersionModel:
        """Record a new version snapshot for a document."""
        version_data = {
            "document_id": document_id,
            "version_number": version_number,
            "storage_path": storage_path,
            "checksum": checksum,
            "uploaded_by": uploaded_by,
            "change_notes": change_notes or f"Version {version_number} upload",
        }
        return await self.repo.create(**version_data)

    async def get_version_history(
        self,
        document_id: uuid.UUID | str,
    ) -> Sequence[DocumentVersionModel]:
        """Fetch complete version history list for a document."""
        return await self.repo.get_by_document_id(document_id)

    async def get_version(
        self,
        document_id: uuid.UUID | str,
        version_number: int,
    ) -> DocumentVersionModel | None:
        """Fetch specific version record."""
        return await self.repo.get_specific_version(document_id, version_number)
