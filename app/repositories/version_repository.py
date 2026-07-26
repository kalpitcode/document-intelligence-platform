"""
Document Version Repository Module
====================================

Data access repository for DocumentVersionModel entities.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentVersionModel
from app.repositories.base import BaseRepository


class VersionRepository(BaseRepository[DocumentVersionModel]):
    """Repository for document historic versions."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DocumentVersionModel, session)

    async def get_by_document_id(
        self,
        document_id: uuid.UUID | str,
    ) -> Sequence[DocumentVersionModel]:
        """Fetch all versions of a document ordered by version number desc."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = (
            select(DocumentVersionModel)
            .where(DocumentVersionModel.document_id == document_id)
            .order_by(DocumentVersionModel.version_number.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_specific_version(
        self,
        document_id: uuid.UUID | str,
        version_number: int,
    ) -> DocumentVersionModel | None:
        """Fetch a specific version of a document by version number."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = (
            select(DocumentVersionModel)
            .where(DocumentVersionModel.document_id == document_id)
            .where(DocumentVersionModel.version_number == version_number)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
