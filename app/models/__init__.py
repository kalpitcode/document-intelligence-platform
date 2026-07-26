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
- DocumentContentModel, DocumentChunkModel, ProcessingJobModel, ExtractedTableModel, ExtractedImageModel, ProcessingStatus
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
from app.models.processing import (
    DocumentChunkModel,
    DocumentContentModel,
    ExtractedImageModel,
    ExtractedTableModel,
    ProcessingJobModel,
    ProcessingStatus,
)
from app.models.role import RoleModel, role_permissions
from app.models.session import UserSessionModel
from app.models.token import RefreshTokenModel
from app.models.user import UserModel, user_roles

from app.models.knowledge import (
    EmbeddingJobModel,
    EmbeddingJobStatus,
    EmbeddingModelModel,
    SearchHistoryModel,
)

__all__ = [
    "AuditLogModel",
    "DocumentChunkModel",
    "DocumentContentModel",
    "DocumentMetadataModel",
    "DocumentModel",
    "DocumentPermissionModel",
    "DocumentStatus",
    "DocumentTagModel",
    "DocumentVersionModel",
    "EmbeddingJobModel",
    "EmbeddingJobStatus",
    "EmbeddingModelModel",
    "ExtractedImageModel",
    "ExtractedTableModel",
    "PermissionModel",
    "ProcessingJobModel",
    "ProcessingStatus",
    "RefreshTokenModel",
    "RoleModel",
    "SearchHistoryModel",
    "UploadSessionModel",
    "UserModel",
    "UserSessionModel",
    "Visibility",
    "document_tags",
    "role_permissions",
    "user_roles",
]
