"""
User Session Repository Module
===============================

Data access repository for UserSessionModel entities.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import UserSessionModel
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[UserSessionModel]):
    """Repository for user session management."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserSessionModel, session)

    async def get_active_sessions(self, user_id: uuid.UUID | str) -> list[UserSessionModel]:
        """Find active sessions (logout_time is None) for a user."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        stmt = select(UserSessionModel).where(
            UserSessionModel.user_id == user_id,
            UserSessionModel.logout_time == None,  # noqa: E711
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
