"""
Repositories Package
=====================

Data access repositories for the Document Intelligence Platform.

Exported repositories:
- BaseRepository
- UserRepository
- RoleRepository
- PermissionRepository
- RefreshTokenRepository
- SessionRepository
- AuditRepository
"""

from __future__ import annotations

from app.repositories.audit_repository import AuditRepository
from app.repositories.base import BaseRepository
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "AuditRepository",
    "BaseRepository",
    "PermissionRepository",
    "RefreshTokenRepository",
    "RoleRepository",
    "SessionRepository",
    "UserRepository",
]
