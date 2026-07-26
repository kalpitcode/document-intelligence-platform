"""
Upload Session Repository Module
=================================

Data access repository for UploadSessionModel entities.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import UploadSessionModel
from app.repositories.base import BaseRepository


class UploadRepository(BaseRepository[UploadSessionModel]):
    """Repository for upload transaction sessions."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UploadSessionModel, session)

    async def get_by_upload_id(self, upload_id: str) -> UploadSessionModel | None:
        """Fetch upload session record by upload transaction ID."""
        stmt = select(UploadSessionModel).where(UploadSessionModel.upload_id == upload_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_by_user(self, user_id: uuid.UUID | str) -> list[UploadSessionModel]:
        """Fetch pending/active upload sessions for a user."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        stmt = (
            select(UploadSessionModel)
            .where(UploadSessionModel.user_id == user_id)
            .where(UploadSessionModel.status.in_(["STARTED", "UPLOADING"]))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
