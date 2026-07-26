"""
Permission Repository Module
=============================

Data access repository for PermissionModel entities.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import PermissionModel
from app.repositories.base import BaseRepository


class PermissionRepository(BaseRepository[PermissionModel]):
    """Repository handling all database operations for permissions."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PermissionModel, session)

    async def get_by_name(self, name: str) -> PermissionModel | None:
        """Find permission by code name (e.g., 'documents.read')."""
        stmt = select(PermissionModel).where(PermissionModel.name == name)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_names(self, names: list[str]) -> Sequence[PermissionModel]:
        """Find multiple permissions by code names."""
        stmt = select(PermissionModel).where(PermissionModel.name.in_(names))
        result = await self.session.execute(stmt)
        return result.scalars().all()
