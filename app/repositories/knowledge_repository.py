"""
Enterprise Knowledge & Vector Search Repository Module
======================================================

Repositories handling database operations for EmbeddingJobModel, SearchHistoryModel,
and EmbeddingModelModel.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import EmbeddingJobModel, EmbeddingModelModel, SearchHistoryModel
from app.repositories.base import BaseRepository


class EmbeddingJobRepository(BaseRepository[EmbeddingJobModel]):
    """Repository managing background vector embedding generation jobs."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(EmbeddingJobModel, session)

    async def get_latest_job(
        self,
        document_id: uuid.UUID | str,
    ) -> EmbeddingJobModel | None:
        """Get the most recent embedding job for a document."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        stmt = (
            select(EmbeddingJobModel)
            .where(EmbeddingJobModel.document_id == document_id)
            .order_by(EmbeddingJobModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class SearchHistoryRepository(BaseRepository[SearchHistoryModel]):
    """Repository managing user search query audit records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SearchHistoryModel, session)

    async def get_user_history(
        self,
        user_id: uuid.UUID | str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[SearchHistoryModel], int]:
        """Get paginated search history for a user."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        stmt = (
            select(SearchHistoryModel)
            .where(SearchHistoryModel.user_id == user_id)
            .order_by(SearchHistoryModel.created_at.desc())
        )

        # Count total
        count_stmt = select(SearchHistoryModel.id).where(SearchHistoryModel.user_id == user_id)
        count_res = await self.session.execute(count_stmt)
        total = len(count_res.scalars().all())

        # Page result
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total


class EmbeddingModelRepository(BaseRepository[EmbeddingModelModel]):
    """Repository managing active embedding model specifications."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(EmbeddingModelModel, session)

    async def get_active_models(self) -> Sequence[EmbeddingModelModel]:
        """Fetch all currently enabled/active embedding models."""
        stmt = (
            select(EmbeddingModelModel)
            .where(EmbeddingModelModel.is_active == True)  # noqa: E712
            .order_by(EmbeddingModelModel.name.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> EmbeddingModelModel | None:
        """Fetch embedding model registry entry by name."""
        stmt = select(EmbeddingModelModel).where(EmbeddingModelModel.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()
