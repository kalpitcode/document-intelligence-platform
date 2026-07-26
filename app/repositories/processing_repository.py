"""
Document Processing Repository Module
=======================================

Repositories handling database queries for DocumentContentModel, DocumentChunkModel,
ProcessingJobModel, ExtractedTableModel, and ExtractedImageModel.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processing import (
    DocumentChunkModel,
    DocumentContentModel,
    ExtractedImageModel,
    ExtractedTableModel,
    ProcessingJobModel,
)
from app.repositories.base import BaseRepository


class DocumentContentRepository(BaseRepository[DocumentContentModel]):
    """Repository managing document extracted text content."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DocumentContentModel, session)

    async def get_by_document_id(
        self,
        document_id: uuid.UUID | str,
    ) -> DocumentContentModel | None:
        """Fetch extracted content record for a given document."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = select(DocumentContentModel).where(
            DocumentContentModel.document_id == document_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class DocumentChunkRepository(BaseRepository[DocumentChunkModel]):
    """Repository managing sequential document chunks."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DocumentChunkModel, session)

    async def get_chunks_by_document_id(
        self,
        document_id: uuid.UUID | str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[DocumentChunkModel], int]:
        """Fetch paginated, ordered text chunks for a document."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = (
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_id == document_id)
            .order_by(DocumentChunkModel.chunk_index.asc())
        )

        # Count total
        count_stmt = select(DocumentChunkModel.id).where(
            DocumentChunkModel.document_id == document_id
        )
        count_res = await self.session.execute(count_stmt)
        total = len(count_res.scalars().all())

        # Page result
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def delete_by_document_id(self, document_id: uuid.UUID | str) -> int:
        """Delete all existing chunks for a document (used during reprocessing)."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = delete(DocumentChunkModel).where(
            DocumentChunkModel.document_id == document_id
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.rowcount


class ProcessingJobRepository(BaseRepository[ProcessingJobModel]):
    """Repository managing processing execution jobs."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ProcessingJobModel, session)

    async def get_latest_job(
        self,
        document_id: uuid.UUID | str,
    ) -> ProcessingJobModel | None:
        """Get the most recent processing job for a document."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = (
            select(ProcessingJobModel)
            .where(ProcessingJobModel.document_id == document_id)
            .order_by(ProcessingJobModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class ExtractedTableRepository(BaseRepository[ExtractedTableModel]):
    """Repository managing extracted document tables."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ExtractedTableModel, session)

    async def get_tables_by_document_id(
        self,
        document_id: uuid.UUID | str,
    ) -> Sequence[ExtractedTableModel]:
        """Get all extracted tables for a document ordered by page and table index."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = (
            select(ExtractedTableModel)
            .where(ExtractedTableModel.document_id == document_id)
            .order_by(ExtractedTableModel.page_number.asc(), ExtractedTableModel.table_index.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_document_id(self, document_id: uuid.UUID | str) -> int:
        """Delete all extracted tables for a document."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = delete(ExtractedTableModel).where(
            ExtractedTableModel.document_id == document_id
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.rowcount


class ExtractedImageRepository(BaseRepository[ExtractedImageModel]):
    """Repository managing extracted embedded document images."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ExtractedImageModel, session)

    async def get_images_by_document_id(
        self,
        document_id: uuid.UUID | str,
    ) -> Sequence[ExtractedImageModel]:
        """Get all extracted image records for a document ordered by page."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = (
            select(ExtractedImageModel)
            .where(ExtractedImageModel.document_id == document_id)
            .order_by(ExtractedImageModel.page_number.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_document_id(self, document_id: uuid.UUID | str) -> int:
        """Delete all extracted images for a document."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = delete(ExtractedImageModel).where(
            ExtractedImageModel.document_id == document_id
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        return res.rowcount
