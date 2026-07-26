"""
Schemas Package
================

Pydantic V2 schemas for API requests, responses, and validation.
"""

from __future__ import annotations

from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.base import APIErrorResponse, APIResponse
from app.schemas.user import PermissionResponse, RoleResponse, UpdateProfileRequest, UserResponse

__all__ = [
    "APIErrorResponse",
    "APIResponse",
    "BaseResponse",
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "LoginRequest",
    "PermissionResponse",
    "RefreshTokenRequest",
    "RegisterRequest",
    "ResendVerificationRequest",
    "ResetPasswordRequest",
    "RoleResponse",
    "TokenResponse",
    "UpdateProfileRequest",
    "UserResponse",
    "VerifyEmailRequest",
]
