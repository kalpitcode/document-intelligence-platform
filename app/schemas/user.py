"""
User & RBAC Schemas Module
===========================

Pydantic V2 models for User profiles, Roles, and Permissions.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PermissionResponse(BaseModel):
    """Permission DTO."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    resource: str
    action: str


class RoleResponse(BaseModel):
    """Role DTO."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    permissions: list[PermissionResponse] = Field(default_factory=list)


class UserResponse(BaseModel):
    """User profile response DTO."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool
    is_superuser: bool
    email_verified: bool
    last_login_at: datetime | None = None
    roles: list[RoleResponse] = Field(default_factory=list)
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    """Update profile payload."""

    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
