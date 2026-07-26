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
- DocumentRepository
- VersionRepository
- MetadataRepository
- UploadRepository
- DocumentContentRepository
- DocumentChunkRepository
- ProcessingJobRepository
- ExtractedTableRepository
- ExtractedImageRepository
"""

from __future__ import annotations

from app.repositories.audit_repository import AuditRepository
from app.repositories.base import BaseRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.metadata_repository import MetadataRepository
from app.repositories.permission_repository import PermissionRepository
from app.repositories.processing_repository import (
    DocumentChunkRepository,
    DocumentContentRepository,
    ExtractedImageRepository,
    ExtractedTableRepository,
    ProcessingJobRepository,
)
from app.repositories.role_repository import RoleRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.token_repository import RefreshTokenRepository
from app.repositories.upload_repository import UploadRepository
from app.repositories.user_repository import UserRepository
from app.repositories.version_repository import VersionRepository

__all__ = [
    "AuditRepository",
    "BaseRepository",
    "DocumentChunkRepository",
    "DocumentContentRepository",
    "DocumentRepository",
    "ExtractedImageRepository",
    "ExtractedTableRepository",
    "MetadataRepository",
    "PermissionRepository",
    "ProcessingJobRepository",
    "RefreshTokenRepository",
    "RoleRepository",
    "SessionRepository",
    "UploadRepository",
    "UserRepository",
    "VersionRepository",
]
