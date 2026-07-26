"""
Models Package
===============

SQLAlchemy ORM models for the Document Intelligence Platform.

Exported models:
- UserModel, user_roles
- RoleModel, role_permissions
- PermissionModel
- RefreshTokenModel
- UserSessionModel
- AuditLogModel
- DocumentModel, DocumentVersionModel, DocumentMetadataModel, UploadSessionModel, DocumentTagModel, DocumentPermissionModel, document_tags, DocumentStatus, Visibility
"""

from __future__ import annotations

from app.models.audit import AuditLogModel
from app.models.document import (
    DocumentMetadataModel,
    DocumentModel,
    DocumentPermissionModel,
    DocumentStatus,
    DocumentTagModel,
    DocumentVersionModel,
    UploadSessionModel,
    Visibility,
    document_tags,
)
from app.models.permission import PermissionModel
from app.models.role import RoleModel, role_permissions
from app.models.session import UserSessionModel
from app.models.token import RefreshTokenModel
from app.models.user import UserModel, user_roles

__all__ = [
    "AuditLogModel",
    "DocumentMetadataModel",
    "DocumentModel",
    "DocumentPermissionModel",
    "DocumentStatus",
    "DocumentTagModel",
    "DocumentVersionModel",
    "PermissionModel",
    "RefreshTokenModel",
    "RoleModel",
    "UploadSessionModel",
    "UserModel",
    "UserSessionModel",
    "Visibility",
    "document_tags",
    "role_permissions",
    "user_roles",
]
