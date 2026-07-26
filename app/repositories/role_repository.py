"""
Role Repository Module
=======================

Data access repository for RoleModel entities.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import RoleModel
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[RoleModel]):
    """Repository handling all database operations for system roles."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RoleModel, session)

    async def get_by_name(self, name: str) -> RoleModel | None:
        """Find role by unique name (e.g. 'Admin', 'Manager', 'User', 'Viewer')."""
        stmt = (
            select(RoleModel)
            .where(RoleModel.name == name)
            .options(selectinload(RoleModel.permissions))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
