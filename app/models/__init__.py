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
from app.models.rag import (
    ChatMessageModel,
    ChatSessionModel,
    LLMUsageLogModel,
    PromptTemplateModel,
)

from app.models.ai import (
    AIFeatureType,
    AIJobModel,
    AIJobStatus,
    AIResultModel,
    FeatureTemplateModel,
)

from app.models.workflow import (
    WorkflowEventModel,
    WorkflowRunModel,
    WorkflowScheduleModel,
    WorkflowStepModel,
    WorkflowTemplateModel,
)

__all__ = [
    "AIFeatureType",
    "AIJobModel",
    "AIJobStatus",
    "AIResultModel",
    "AuditLogModel",
    "ChatMessageModel",
    "ChatSessionModel",
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
    "FeatureTemplateModel",
    "LLMUsageLogModel",
    "PermissionModel",
    "ProcessingJobModel",
    "ProcessingStatus",
    "PromptTemplateModel",
    "RefreshTokenModel",
    "RoleModel",
    "SearchHistoryModel",
    "UploadSessionModel",
    "UserModel",
    "UserSessionModel",
    "Visibility",
    "WorkflowEventModel",
    "WorkflowRunModel",
    "WorkflowScheduleModel",
    "WorkflowStepModel",
    "WorkflowTemplateModel",
    "document_tags",
    "role_permissions",
    "user_roles",
]
