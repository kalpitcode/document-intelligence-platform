"""
Auth Dependencies Module
========================

FastAPI security dependencies for authentication, RBAC authorization, and resource ownership checks.

**Architectural Rationale:**
- Reusable dependency functions injected into route endpoints via `Depends()`.
- Validates Bearer token using OAuth2PasswordBearer standard.
- Checks Redis blacklist and token version for immediate revocation enforcement.
- Provides granular role, permission, and ownership checks.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_async_session
from app.core.exceptions.base import (
    AuthenticationException,
    PermissionDeniedException,
    ResourceForbiddenException,
    RoleRequiredException,
)
from app.models.user import UserModel
from app.repositories.user_repository import UserRepository
from app.services.cache_service import CacheService
from app.services.token_service import TokenService

# OAuth2 Bearer scheme pointing to login endpoint
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> UserModel:
    """
    Extract and validate the current authenticated user from Bearer token.
    """
    if not token:
        raise AuthenticationException(message="Not authenticated (Bearer token missing)")

    payload = TokenService.decode_token(token, expected_type="access")
    jti = payload.get("jti")
    user_id = payload.get("sub")
    token_version = payload.get("token_version", 1)

    if jti and await CacheService.is_token_blacklisted(jti):
        raise AuthenticationException(message="Token has been revoked")

    user_repo = UserRepository(session)
    user = await user_repo.get_with_roles_and_permissions(user_id)

    if not user or not user.is_active:
        raise AuthenticationException(message="User not found or account deactivated")

    if user.token_version != token_version:
        raise AuthenticationException(message="Token version outdated (bulk logout executed)")

    return user


def require_role(*required_roles: str) -> Callable[..., UserModel]:
    """
    Dependency factory to enforce role-based access control (RBAC).
    """

    async def role_checker(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.is_superuser:
            return current_user

        user_roles = [r.name for r in current_user.roles]
        for role in required_roles:
            if role in user_roles:
                return current_user

        raise RoleRequiredException(
            message=f"Access requires one of the following roles: {list(required_roles)}"
        )

    return role_checker


def require_permission(*required_permissions: str) -> Callable[..., UserModel]:
    """
    Dependency factory to enforce fine-grained permission-based authorization.
    """

    async def permission_checker(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.is_superuser:
            return current_user

        # Collect user permissions from assigned roles
        user_permissions = set()
        for role in current_user.roles:
            for perm in role.permissions:
                user_permissions.add(perm.name)

        # Super admin full permission shortcut
        if "admin.full" in user_permissions:
            return current_user

        for req_perm in required_permissions:
            if req_perm in user_permissions:
                return current_user

        raise PermissionDeniedException(
            message=f"Access requires permission: {list(required_permissions)}"
        )

    return permission_checker


async def get_current_admin(
    current_user: UserModel = Depends(require_role("Admin")),
) -> UserModel:
    """Dependency enforcing Admin role."""
    return current_user


def require_ownership_or_admin(resource_user_id_param: str = "id") -> Callable[..., UserModel]:
    """
    Dependency checking that the current user owns the requested resource OR has Admin role.
    """

    async def ownership_checker(
        request: Request,
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        if current_user.is_superuser or any(r.name == "Admin" for r in current_user.roles):
            return current_user

        target_id_str = request.path_params.get(resource_user_id_param)
        if target_id_str and str(current_user.id) == str(target_id_str):
            return current_user

        raise ResourceForbiddenException(
            message="You are not authorized to access or modify another user's resource"
        )

    return ownership_checker
