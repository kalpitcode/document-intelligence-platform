"""
Role Service Module
====================

Business service for Role and RBAC assignment management.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.events.base import EventBus, PermissionGranted
from app.core.exceptions.base import EntityNotFoundException
from app.models.role import RoleModel
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository


class RoleService:
    """Service handling system roles and permission assignment."""

    def __init__(
        self,
        role_repo: RoleRepository,
        permission_repo: PermissionRepository,
    ) -> None:
        self.role_repo = role_repo
        self.permission_repo = permission_repo

    async def get_all_roles(self) -> Sequence[RoleModel]:
        """Get all roles."""
        return await self.role_repo.get_all()

    async def get_role_by_name(self, name: str) -> RoleModel:
        """Get role by name or raise EntityNotFoundException."""
        role = await self.role_repo.get_by_name(name)
        if not role:
            raise EntityNotFoundException(entity_type="Role", entity_id=name)
        return role

    async def create_role(self, name: str, description: str | None = None) -> RoleModel:
        """Create a new security role."""
        return await self.role_repo.create(name=name, description=description)

    async def assign_permissions_to_role(
        self,
        role_name: str,
        permission_names: list[str],
    ) -> RoleModel:
        """Link permissions to a role."""
        role = await self.get_role_by_name(role_name)
        permissions = await self.permission_repo.get_by_names(permission_names)

        role.permissions = list(permissions)
        await self.role_repo.session.flush()

        for p in permission_names:
            EventBus.publish(PermissionGranted(role_name=role_name, permission_name=p))

        return role
