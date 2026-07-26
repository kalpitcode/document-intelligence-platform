"""
Auth Schemas Module
====================

Pydantic V2 models for authentication requests and responses.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Registration request payload."""

    email: EmailStr = Field(..., description="Valid user email address", examples=["user@example.com"])
    username: str = Field(..., min_length=3, max_length=50, description="Unique username handle", examples=["johndoe"])
    password: str = Field(..., min_length=12, description="Plaintext password complying with complexity policy")
    first_name: str | None = Field(None, max_length=100, description="First name")
    last_name: str | None = Field(None, max_length=100, description="Last name")


class LoginRequest(BaseModel):
    """Login request payload."""

    email_or_username: str = Field(..., description="User email or username handle", examples=["user@example.com"])
    password: str = Field(..., description="Plaintext password")


class TokenResponse(BaseModel):
    """JWT Token pair response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


class RefreshTokenRequest(BaseModel):
    """Refresh token request payload."""

    refresh_token: str = Field(..., description="Active refresh token JWT")


class ChangePasswordRequest(BaseModel):
    """Change password payload."""

    current_password: str = Field(..., description="Current plaintext password")
    new_password: str = Field(..., min_length=12, description="New plaintext password")


class ForgotPasswordRequest(BaseModel):
    """Forgot password payload."""

    email: EmailStr = Field(..., description="User registered email address")


class ResetPasswordRequest(BaseModel):
    """Reset password payload."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=12, description="New plaintext password")


class VerifyEmailRequest(BaseModel):
    """Verify email payload."""

    token: str = Field(..., description="Email verification token")


class ResendVerificationRequest(BaseModel):
    """Resend email verification payload."""

    email: EmailStr = Field(..., description="User registered email address")
