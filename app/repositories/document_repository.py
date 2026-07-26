"""
Document Repository Module
===========================

Data access repository for DocumentModel entities.
"""

from __future__ import annotations

from datetime import datetime
import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import DocumentModel, DocumentVersionModel
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[DocumentModel]):
    """Repository handling database operations for managed documents."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DocumentModel, session)

    async def get_by_id_with_relations(
        self,
        document_id: uuid.UUID | str,
    ) -> DocumentModel | None:
        """Fetch document by ID eagerly loading versions, metadata, and tags."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = (
            select(DocumentModel)
            .where(getattr(DocumentModel, "id") == document_id)
            .where(DocumentModel.deleted_at.is_(None))
            .options(
                selectinload(DocumentModel.versions),
                selectinload(DocumentModel.metadata_record),
                selectinload(DocumentModel.tags),
                selectinload(DocumentModel.permissions),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_sha256(self, sha256_hash: str) -> DocumentModel | None:
        """Find active document by SHA256 content hash (for duplicate check)."""
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.sha256_hash == sha256_hash)
            .where(DocumentModel.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_documents(
        self,
        owner_id: uuid.UUID | str | None = None,
        filename: str | None = None,
        status: str | None = None,
        visibility: str | None = None,
        mime_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[DocumentModel], int]:
        """
        List documents with multi-field filtering, sorting, and pagination.

        Returns:
            Tuple of (items_list, total_count).
        """
        stmt = select(DocumentModel).where(DocumentModel.deleted_at.is_(None))

        # Filter criteria
        if owner_id:
            if isinstance(owner_id, str):
                owner_id = uuid.UUID(owner_id)
            stmt = stmt.where(DocumentModel.owner_id == owner_id)

        if filename:
            stmt = stmt.where(DocumentModel.original_filename.ilike(f"%{filename.strip()}%"))

        if status:
            stmt = stmt.where(DocumentModel.status == status)

        if visibility:
            stmt = stmt.where(DocumentModel.visibility == visibility)

        if mime_type:
            stmt = stmt.where(DocumentModel.mime_type == mime_type)

        if date_from:
            stmt = stmt.where(DocumentModel.created_at >= date_from)

        if date_to:
            stmt = stmt.where(DocumentModel.created_at <= date_to)

        # Count query
        count_stmt = select(DocumentModel.id).from_statement(stmt)
        count_res = await self.session.execute(count_stmt)
        total_count = len(count_res.scalars().all())

        # Sorting mapping
        sort_column_map = {
            "created_at": DocumentModel.created_at,
            "updated_at": DocumentModel.updated_at,
            "filename": DocumentModel.original_filename,
            "size": DocumentModel.file_size,
        }
        target_col = sort_column_map.get(sort_by, DocumentModel.created_at)

        if sort_order.lower() == "asc":
            stmt = stmt.order_by(target_col.asc())
        else:
            stmt = stmt.order_by(target_col.desc())

        # Eager loads and pagination
        stmt = (
            stmt.options(
                selectinload(DocumentModel.versions),
                selectinload(DocumentModel.metadata_record),
                selectinload(DocumentModel.tags),
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all(), total_count
