"""
Document Metadata Repository Module
====================================

Data access repository for DocumentMetadataModel entities.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentMetadataModel
from app.repositories.base import BaseRepository


class MetadataRepository(BaseRepository[DocumentMetadataModel]):
    """Repository for technical and custom document metadata."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DocumentMetadataModel, session)

    async def get_by_document_id(
        self,
        document_id: uuid.UUID | str,
    ) -> DocumentMetadataModel | None:
        """Fetch metadata record by document ID."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = select(DocumentMetadataModel).where(DocumentMetadataModel.document_id == document_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()
