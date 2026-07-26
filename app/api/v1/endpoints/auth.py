"""
Authentication Router Endpoint Module
======================================

FastAPI endpoints for registration, login, token refresh, logout, password management, and email verification.

**Architectural Rationale:**
- Pure HTTP controller layer: validates request schemas, delegates work to AuthService, returns standard APIResponse.
- Fully documented OpenAPI metadata for API consumers.
"""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_async_session
from app.dependencies.auth import get_current_user, oauth2_scheme
from app.models.user import UserModel
from app.repositories.audit_repository import AuditRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.schemas.base import APIResponse
from app.schemas.user import UserResponse
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.cache_service import CacheService
from app.services.email_service import EmailService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_service(session: AsyncSession = Depends(get_async_session)) -> AuthService:
    """Dependency injector constructing AuthService instance."""
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    token_repo = RefreshTokenRepository(session)
    session_repo = SessionRepository(session)
    audit_repo = AuditRepository(session)
    audit_service = AuditService(audit_repo)
    return AuthService(user_repo, role_repo, token_repo, session_repo, audit_service)


@router.post(
    "/register",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with Argon2id password hashing and default role assignment.",
)
async def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[UserResponse]:
    """Register user account."""
    user = await auth_service.register(
        email=payload.email,
        username=payload.username,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    return APIResponse(
        success=True,
        message="User registered successfully. Verification email sent.",
        data=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=APIResponse[dict[str, Any]],
    summary="User Login",
    description="Authenticate user credentials and receive access and refresh token pair.",
)
async def login(
    payload: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[dict[str, Any]]:
    """Authenticate user."""
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    result = await auth_service.login(
        email_or_username=payload.email_or_username,
        password=payload.password,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    user_data = UserResponse.model_validate(result["user"]).model_dump(mode="json")
    return APIResponse(
        success=True,
        message="Login successful",
        data={
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
            "user": user_data,
        },
    )


@router.post(
    "/logout",
    response_model=APIResponse[dict[str, bool]],
    summary="User Logout",
    description="Blacklist active Bearer access token and revoke refresh token.",
)
async def logout(
    payload: RefreshTokenRequest | None = None,
    token: str | None = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[dict[str, bool]]:
    """Logout user."""
    if token:
        ref_jwt = payload.refresh_token if payload else None
        await auth_service.logout(access_token=token, refresh_token_jwt=ref_jwt)

    return APIResponse(
        success=True,
        message="Successfully logged out",
        data={"logged_out": True},
    )


@router.post(
    "/refresh",
    response_model=APIResponse[dict[str, Any]],
    summary="Refresh Access Token",
    description="Exchange a valid refresh token for a new access token and rotated refresh token.",
)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[dict[str, Any]]:
    """Refresh token pair."""
    tokens = await auth_service.refresh_tokens(payload.refresh_token)
    return APIResponse(
        success=True,
        message="Token refreshed successfully",
        data=tokens,
    )


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get Current Authenticated User Profile",
    description="Return active authenticated user details.",
)
async def get_me(
    current_user: UserModel = Depends(get_current_user),
) -> APIResponse[UserResponse]:
    """Return profile of current user."""
    return APIResponse(
        success=True,
        message="Current user profile retrieved successfully",
        data=UserResponse.model_validate(current_user),
    )


@router.post(
    "/change-password",
    response_model=APIResponse[dict[str, bool]],
    summary="Change User Password",
    description="Change current user password after complexity validation.",
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[dict[str, bool]]:
    """Change password."""
    await auth_service.change_password(
        user_id=current_user.id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return APIResponse(
        success=True,
        message="Password updated successfully",
        data={"updated": True},
    )


@router.post(
    "/forgot-password",
    response_model=APIResponse[dict[str, bool]],
    summary="Request Password Reset",
    description="Trigger mock password reset link to user email.",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[dict[str, bool]]:
    """Send reset password link."""
    await auth_service.forgot_password(email=payload.email)
    return APIResponse(
        success=True,
        message="If email exists, a password reset link has been dispatched.",
        data={"sent": True},
    )


@router.post(
    "/reset-password",
    response_model=APIResponse[dict[str, bool]],
    summary="Reset Password with Token",
    description="Reset password using valid reset token.",
)
async def reset_password(
    payload: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[dict[str, bool]]:
    """Reset password."""
    await auth_service.reset_password(token=payload.token, new_password=payload.new_password)
    return APIResponse(
        success=True,
        message="Password has been reset successfully.",
        data={"reset": True},
    )


@router.post(
    "/verify-email",
    response_model=APIResponse[dict[str, bool]],
    summary="Verify Email Address",
    description="Verify email address using verification token.",
)
async def verify_email(
    payload: VerifyEmailRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[dict[str, bool]]:
    """Verify email."""
    await auth_service.verify_email(token=payload.token)
    return APIResponse(
        success=True,
        message="Email address verified successfully.",
        data={"verified": True},
    )


@router.post(
    "/resend-verification",
    response_model=APIResponse[dict[str, bool]],
    summary="Resend Verification Email",
    description="Resend mock email verification token.",
)
async def resend_verification(
    payload: ResendVerificationRequest,
    session: AsyncSession = Depends(get_async_session),
) -> APIResponse[dict[str, bool]]:
    """Resend email verification."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_email(payload.email)
    if user and not user.email_verified:
        token = secrets.token_urlsafe(32)
        await CacheService.store_temporary_token("email_verify", token, str(user.id), ttl_seconds=86400)
        await EmailService.send_verification_email(user.email, token)

    return APIResponse(
        success=True,
        message="If unverified account exists, verification email has been resent.",
        data={"sent": True},
    )
