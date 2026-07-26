"""
Authentication Service Module
==============================

Coordinates complete authentication, token issuance, and account security workflows.
"""

from __future__ import annotations

import secrets
import uuid
from typing import Any

from app.core.events.base import (
    EventBus,
    PasswordChanged,
    UserLoggedIn,
    UserRegistered,
)
from app.core.exceptions.base import (
    AccountLockedException,
    AuthenticationException,
    EntityNotFoundException,
    InvalidCredentialsException,
    ValidationException,
)
from app.models.user import UserModel
from app.repositories.role_repository import RoleRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.services.cache_service import CacheService
from app.services.email_service import EmailService
from app.services.password_service import PasswordService
from app.services.token_service import TokenService
from app.utils.time import utc_now


class AuthService:
    """Service orchestrating authentication flows."""

    def __init__(
        self,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        token_repo: RefreshTokenRepository,
        session_repo: SessionRepository,
        audit_service: AuditService,
    ) -> None:
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.token_repo = token_repo
        self.session_repo = session_repo
        self.audit_service = audit_service

    async def register(
        self,
        email: str,
        username: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> UserModel:
        """Register a new user account."""
        normalized_email = email.lower().strip()
        normalized_username = username.strip()

        # Email & Username uniqueness check
        existing_email = await self.user_repo.get_by_email(normalized_email)
        if existing_email:
            raise ValidationException(
                message="Email address is already registered",
                errors=[{"field": "email", "message": "Email is already taken", "type": "unique"}],
            )

        existing_username = await self.user_repo.get_by_username(normalized_username)
        if existing_username:
            raise ValidationException(
                message="Username is already taken",
                errors=[{"field": "username", "message": "Username is already taken", "type": "unique"}],
            )

        # Password complexity validation
        PasswordService.validate_password_complexity(password)
        hashed_password = PasswordService.hash_password(password)

        # Create user instance
        user = await self.user_repo.create(
            email=normalized_email,
            username=normalized_username,
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_superuser=False,
            email_verified=False,
            token_version=1,
        )

        # Assign default 'User' role
        default_role = await self.role_repo.get_by_name("User")
        if not default_role:
            default_role = await self.role_repo.create(name="User", description="Default user role")
        user.roles.append(default_role)
        await self.user_repo.session.flush()

        # Publish domain event
        EventBus.publish(UserRegistered(user_id=str(user.id), email=user.email, username=user.username))

        # Log audit entry
        await self.audit_service.log_event(
            action="USER_REGISTERED",
            user_id=user.id,
            target_resource=f"user:{user.id}",
            status="SUCCESS",
        )

        # Trigger mock email verification link
        token = secrets.token_urlsafe(32)
        await CacheService.store_temporary_token("email_verify", token, str(user.id), ttl_seconds=86400)
        await EmailService.send_verification_email(user.email, token)

        return user

    async def login(
        self,
        email_or_username: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Authenticate user and return token pair and user details."""
        identifier = email_or_username.strip().lower()

        # Lockout check
        if await CacheService.is_account_locked(identifier):
            await self.audit_service.log_event(
                action="USER_LOGIN_FAILED_LOCKED",
                target_resource=f"identifier:{identifier}",
                status="FAILURE",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise AccountLockedException()

        # Find user by email or username
        user = await self.user_repo.get_by_email(identifier)
        if not user:
            user = await self.user_repo.get_by_username(email_or_username.strip())

        if not user or not PasswordService.verify_password(password, user.hashed_password):
            failed_attempts = await CacheService.record_failed_login(identifier)
            await self.audit_service.log_event(
                action="USER_LOGIN_FAILED",
                target_resource=f"identifier:{identifier}",
                status="FAILURE",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"failed_attempts": failed_attempts},
            )
            raise InvalidCredentialsException()

        if not user.is_active:
            raise AuthenticationException(message="User account is deactivated")

        # Clear failed logins on success
        await CacheService.clear_failed_logins(identifier)

        # Load roles & permissions
        user_full = await self.user_repo.get_with_roles_and_permissions(user.id)
        role_names = [r.name for r in user_full.roles] if user_full else []
        perm_names = []
        if user_full:
            for r in user_full.roles:
                for p in r.permissions:
                    if p.name not in perm_names:
                        perm_names.append(p.name)

        # Generate tokens
        access_token = TokenService.create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            token_version=user.token_version,
            roles=role_names,
            permissions=perm_names,
        )

        refresh_token_jwt, jti, expires_at = TokenService.create_refresh_token(
            user_id=user.id,
            token_version=user.token_version,
        )

        # Record RefreshToken in DB
        now = utc_now()
        await self.token_repo.create(
            user_id=user.id,
            jti=jti,
            ip_address=ip_address,
            browser=user_agent,
            issued_at=now,
            expires_at=expires_at,
            is_revoked=False,
        )

        # Record UserSession in DB
        session = await self.session_repo.create(
            user_id=user.id,
            browser=user_agent,
            ip=ip_address,
            login_time=now,
            last_activity=now,
        )

        # Update last login info
        user.last_login_at = now
        user.last_login_ip = ip_address
        user.failed_login_attempts = 0
        await self.user_repo.session.flush()

        # Audit log & domain event
        await self.audit_service.log_event(
            action="USER_LOGIN_SUCCESS",
            user_id=user.id,
            target_resource=f"user:{user.id}",
            status="SUCCESS",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        EventBus.publish(UserLoggedIn(user_id=str(user.id), email=user.email, ip_address=ip_address, user_agent=user_agent))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_jwt,
            "token_type": "bearer",
            "expires_in": 1800,
            "user": user_full,
            "session_id": str(session.id),
        }

    async def refresh_tokens(self, refresh_token_jwt: str) -> dict[str, str]:
        """Validate refresh token and issue rotated token pair."""
        payload = TokenService.decode_token(refresh_token_jwt, expected_type="refresh")
        user_id = payload["sub"]
        jti = payload["jti"]
        token_version = payload.get("token_version", 1)

        # Check Redis blacklist
        if await CacheService.is_token_blacklisted(jti):
            raise AuthenticationException(message="Refresh token has been revoked")

        # Check DB record
        token_record = await self.token_repo.get_by_jti(jti)
        if not token_record or token_record.is_revoked:
            raise AuthenticationException(message="Refresh token is invalid or revoked")

        user = await self.user_repo.get_with_roles_and_permissions(user_id)
        if not user or not user.is_active or user.token_version != token_version:
            raise AuthenticationException(message="Invalid session or token version")

        # Revoke old refresh token (rotation)
        token_record.is_revoked = True
        token_record.revoked_at = utc_now()

        role_names = [r.name for r in user.roles]
        perm_names = [p.name for r in user.roles for p in r.permissions]

        new_access_token = TokenService.create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            token_version=user.token_version,
            roles=role_names,
            permissions=perm_names,
        )

        new_refresh_token_jwt, new_jti, new_expires_at = TokenService.create_refresh_token(
            user_id=user.id,
            token_version=user.token_version,
        )

        await self.token_repo.create(
            user_id=user.id,
            jti=new_jti,
            issued_at=utc_now(),
            expires_at=new_expires_at,
            is_revoked=False,
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token_jwt,
            "token_type": "bearer",
            "expires_in": 1800,
        }

    async def logout(self, access_token: str, refresh_token_jwt: str | None = None) -> None:
        """Logout user by blacklisting tokens."""
        try:
            payload = TokenService.decode_token(access_token, expected_type="access")
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                ttl = max(1, exp - int(utc_now().timestamp()))
                await CacheService.blacklist_token(jti, ttl)
        except Exception:
            pass

        if refresh_token_jwt:
            try:
                ref_payload = TokenService.decode_token(refresh_token_jwt, expected_type="refresh")
                ref_jti = ref_payload.get("jti")
                if ref_jti:
                    token_rec = await self.token_repo.get_by_jti(ref_jti)
                    if token_rec:
                        token_rec.is_revoked = True
                        token_rec.revoked_at = utc_now()
            except Exception:
                pass

    async def change_password(
        self,
        user_id: uuid.UUID | str,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change current user password."""
        user = await self.user_repo.get_by_id(user_id)
        if not user or not PasswordService.verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsException(message="Current password is incorrect")

        PasswordService.validate_password_complexity(new_password)
        user.hashed_password = PasswordService.hash_password(new_password)
        user.token_version += 1
        await self.user_repo.session.flush()

        await self.audit_service.log_event(
            action="PASSWORD_CHANGED",
            user_id=user.id,
            target_resource=f"user:{user.id}",
            status="SUCCESS",
        )
        EventBus.publish(PasswordChanged(user_id=str(user.id), email=user.email))

    async def forgot_password(self, email: str) -> None:
        """Mock forgot password token generation."""
        user = await self.user_repo.get_by_email(email)
        if user:
            token = secrets.token_urlsafe(32)
            await CacheService.store_temporary_token("password_reset", token, str(user.id), ttl_seconds=3600)
            await EmailService.send_password_reset_email(user.email, token)

    async def reset_password(self, token: str, new_password: str) -> None:
        """Reset password using token."""
        user_id = await CacheService.get_temporary_token_value("password_reset", token)
        if not user_id:
            raise ValidationException(message="Password reset token is invalid or has expired")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException(entity_type="User", entity_id=user_id)

        PasswordService.validate_password_complexity(new_password)
        user.hashed_password = PasswordService.hash_password(new_password)
        user.token_version += 1
        await self.user_repo.session.flush()

        await CacheService.delete_temporary_token("password_reset", token)
        await self.audit_service.log_event(
            action="PASSWORD_RESET",
            user_id=user.id,
            target_resource=f"user:{user.id}",
            status="SUCCESS",
        )

    async def verify_email(self, token: str) -> None:
        """Verify user email address using token."""
        user_id = await CacheService.get_temporary_token_value("email_verify", token)
        if not user_id:
            raise ValidationException(message="Email verification token is invalid or has expired")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException(entity_type="User", entity_id=user_id)

        user.email_verified = True
        user.email_verified_at = utc_now()
        await self.user_repo.session.flush()

        await CacheService.delete_temporary_token("email_verify", token)
