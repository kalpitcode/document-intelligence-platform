"""
User Service Module
====================

Business service for user profile queries and updates.
"""

from __future__ import annotations

import uuid

from app.core.exceptions.base import EntityNotFoundException
from app.models.user import UserModel
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


class UserService:
    """Service providing user management and ownership authorization checks."""

    def __init__(self, user_repo: UserRepository, role_repo: RoleRepository) -> None:
        self.user_repo = user_repo
        self.role_repo = role_repo

    async def get_by_id(self, user_id: uuid.UUID | str) -> UserModel:
        """Fetch user by ID or raise EntityNotFoundException."""
        user = await self.user_repo.get_with_roles_and_permissions(user_id)
        if not user:
            raise EntityNotFoundException(entity_type="User", entity_id=str(user_id))
        return user

    async def update_profile(
        self,
        user_id: uuid.UUID | str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> UserModel:
        """Update profile information."""
        user = await self.get_by_id(user_id)
        kwargs = {}
        if first_name is not None:
            kwargs["first_name"] = first_name
        if last_name is not None:
            kwargs["last_name"] = last_name

        return await self.user_repo.update(user, **kwargs)

    async def assign_role_to_user(
        self,
        user_id: uuid.UUID | str,
        role_name: str,
    ) -> UserModel:
        """Assign a role to a user account."""
        user = await self.get_by_id(user_id)
        role = await self.role_repo.get_by_name(role_name)
        if not role:
            raise EntityNotFoundException(entity_type="Role", entity_id=role_name)

        if role not in user.roles:
            user.roles.append(role)
            await self.user_repo.session.flush()

        return user
