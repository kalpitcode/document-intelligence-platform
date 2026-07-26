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
from app.schemas.document import (
    DocumentDownloadResponse,
    DocumentMetadataResponse,
    DocumentResponse,
    DocumentTagResponse,
    DocumentUpdate,
    DocumentVersionResponse,
    UploadSessionResponse,
)
from app.schemas.processing import (
    DocumentChunkResponse,
    DocumentContentResponse,
    ExtractedImageResponse,
    ExtractedTableResponse,
    ProcessTriggerResponse,
    ProcessingJobResponse,
)
from app.schemas.user import PermissionResponse, RoleResponse, UpdateProfileRequest, UserResponse

from app.schemas.knowledge import (
    EmbeddingModelResponse,
    QueryTypeEnum,
    ReindexRequest,
    ReindexResponse,
    SearchFilterSchema,
    SearchHistoryItemResponse,
    SearchHistoryListResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

__all__ = [
    "APIErrorResponse",
    "APIResponse",
    "ChangePasswordRequest",
    "DocumentChunkResponse",
    "DocumentContentResponse",
    "DocumentDownloadResponse",
    "DocumentMetadataResponse",
    "DocumentResponse",
    "DocumentTagResponse",
    "DocumentUpdate",
    "DocumentVersionResponse",
    "EmbeddingModelResponse",
    "ExtractedImageResponse",
    "ExtractedTableResponse",
    "ForgotPasswordRequest",
    "LoginRequest",
    "PermissionResponse",
    "ProcessTriggerResponse",
    "ProcessingJobResponse",
    "QueryTypeEnum",
    "RefreshTokenRequest",
    "RegisterRequest",
    "ReindexRequest",
    "ReindexResponse",
    "ResendVerificationRequest",
    "ResetPasswordRequest",
    "RoleResponse",
    "SearchFilterSchema",
    "SearchHistoryItemResponse",
    "SearchHistoryListResponse",
    "SearchRequest",
    "SearchResponse",
    "SearchResultItem",
    "TokenResponse",
    "UpdateProfileRequest",
    "UploadSessionResponse",
    "UserResponse",
    "VerifyEmailRequest",
]
