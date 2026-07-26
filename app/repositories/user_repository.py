"""
User Repository Module
======================

Data access repository for UserModel entities.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import RoleModel
from app.models.user import UserModel
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    """Repository handling all database operations for User accounts."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserModel, session)

    async def get_by_email(self, email: str) -> UserModel | None:
        """Find a user by normalized email address."""
        stmt = (
            select(UserModel)
            .where(UserModel.email == email.lower().strip())
            .where(UserModel.deleted_at.is_(None))
            .options(selectinload(UserModel.roles))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_username(self, username: str) -> UserModel | None:
        """Find a user by unique username handle."""
        stmt = (
            select(UserModel)
            .where(UserModel.username == username.strip())
            .where(UserModel.deleted_at.is_(None))
            .options(selectinload(UserModel.roles))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_with_roles_and_permissions(self, user_id: uuid.UUID | str) -> UserModel | None:
        """
        Get user with eager loading of roles and role permissions.
        """
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        stmt = (
            select(UserModel)
            .where(UserModel.id == user_id)
            .where(UserModel.deleted_at.is_(None))
            .options(selectinload(UserModel.roles).selectinload(RoleModel.permissions))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def increment_token_version(self, user_id: uuid.UUID | str) -> int:
        """
        Increment user's token version to invalidate all currently active JWTs.
        """
        user = await self.get_by_id(user_id)
        if not user:
            return 0
        user.token_version += 1
        self.session.add(user)
        await self.session.flush()
        return user.token_version
