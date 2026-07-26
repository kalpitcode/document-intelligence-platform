"""
Permission Service Module
==========================

Business service for Permission management.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.models.permission import PermissionModel
from app.repositories.permission_repository import PermissionRepository


class PermissionService:
    """Service providing Permission management logic."""

    def __init__(self, permission_repo: PermissionRepository) -> None:
        self.permission_repo = permission_repo

    async def get_all_permissions(self) -> Sequence[PermissionModel]:
        """Fetch all registered system permissions."""
        return await self.permission_repo.get_all(limit=500)

    async def create_permission(
        self,
        name: str,
        resource: str,
        action: str,
        description: str | None = None,
    ) -> PermissionModel:
        """Create a new system permission code."""
        return await self.permission_repo.create(
            name=name,
            resource=resource,
            action=action,
            description=description,
        )
