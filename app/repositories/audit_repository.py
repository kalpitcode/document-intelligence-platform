"""
Audit Log Repository Module
============================

Data access repository for AuditLogModel entities.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLogModel
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLogModel]):
    """Repository for managing audit log records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuditLogModel, session)

    async def get_by_user_id(
        self,
        user_id: uuid.UUID | str,
        limit: int = 100,
    ) -> Sequence[AuditLogModel]:
        """Fetch audit logs for a specific user."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        stmt = (
            select(AuditLogModel)
            .where(AuditLogModel.user_id == user_id)
            .order_by(AuditLogModel.timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
