"""
Refresh Token Repository Module
=================================

Data access repository for RefreshTokenModel entities.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token import RefreshTokenModel
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshTokenModel]):
    """Repository for managing persistence and rotation of refresh tokens."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RefreshTokenModel, session)

    async def get_by_jti(self, jti: str) -> RefreshTokenModel | None:
        """Find refresh token record by unique JTI."""
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.jti == jti)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def revoke_user_tokens(self, user_id: uuid.UUID | str) -> None:
        """Mark all active refresh tokens for a user as revoked."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.is_revoked == False,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        tokens = result.scalars().all()
        for token in tokens:
            token.is_revoked = True
        self.session.add_all(tokens)
        await self.session.flush()
