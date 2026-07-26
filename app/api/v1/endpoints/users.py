"""
Users Router Endpoint Module
=============================

FastAPI endpoints for user profile management and user lookup.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_async_session
from app.dependencies.auth import get_current_user, require_ownership_or_admin
from app.models.user import UserModel
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.base import APIResponse
from app.schemas.user import UpdateProfileRequest, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service(session: AsyncSession = Depends(get_async_session)) -> UserService:
    """Dependency injector constructing UserService instance."""
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    return UserService(user_repo, role_repo)


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get My Profile",
    description="Retrieve the profile of the current authenticated user.",
)
async def get_my_profile(
    current_user: UserModel = Depends(get_current_user),
) -> APIResponse[UserResponse]:
    """Return profile of authenticated user."""
    return APIResponse(
        success=True,
        message="Profile retrieved successfully",
        data=UserResponse.model_validate(current_user),
    )


@router.put(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Update My Profile",
    description="Update profile details (first name, last name) of current authenticated user.",
)
async def update_my_profile(
    payload: UpdateProfileRequest,
    current_user: UserModel = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> APIResponse[UserResponse]:
    """Update authenticated user profile."""
    updated_user = await user_service.update_profile(
        user_id=current_user.id,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    return APIResponse(
        success=True,
        message="Profile updated successfully",
        data=UserResponse.model_validate(updated_user),
    )


@router.get(
    "/{id}",
    response_model=APIResponse[UserResponse],
    summary="Get User By ID",
    description="Retrieve user profile by ID. Restricted to account owner or Admin role.",
)
async def get_user_by_id(
    id: uuid.UUID,
    user_service: UserService = Depends(get_user_service),
    current_user: UserModel = Depends(require_ownership_or_admin("id")),
) -> APIResponse[UserResponse]:
    """Retrieve user by ID."""
    user = await user_service.get_by_id(id)
    return APIResponse(
        success=True,
        message="User profile retrieved successfully",
        data=UserResponse.model_validate(user),
    )
