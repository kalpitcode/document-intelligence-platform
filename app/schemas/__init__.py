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
from app.schemas.rag import (
    ChatMessageResponse,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    CitationItem,
    LatencyMetrics,
    RAGChatRequest,
    RAGChatResponse,
    RetrievedDocumentItem,
    TokenUsage,
)

from app.schemas.ai import (
    AIJobResponse,
    AIResultResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    ClassifyRequest,
    ClassifyResponse,
    ExtractRequest,
    ExtractResponse,
    SummarizeRequest,
    SummarizeResponse,
    SummaryTypeEnum,
    TranslateRequest,
    TranslateResponse,
)

__all__ = [
    "AIJobResponse",
    "AIResultResponse",
    "APIErrorResponse",
    "APIResponse",
    "AnalyzeRequest",
    "AnalyzeResponse",
    "ChangePasswordRequest",
    "ChatMessageResponse",
    "ChatSessionDetailResponse",
    "ChatSessionListResponse",
    "ChatSessionResponse",
    "CitationItem",
    "ClassifyRequest",
    "ClassifyResponse",
    "DocumentChunkResponse",
    "DocumentContentResponse",
    "DocumentDownloadResponse",
    "DocumentMetadataResponse",
    "DocumentResponse",
    "DocumentTagResponse",
    "DocumentUpdate",
    "DocumentVersionResponse",
    "EmbeddingModelResponse",
    "ExtractRequest",
    "ExtractResponse",
    "ExtractedImageResponse",
    "ExtractedTableResponse",
    "ForgotPasswordRequest",
    "LatencyMetrics",
    "LoginRequest",
    "PermissionResponse",
    "ProcessTriggerResponse",
    "ProcessingJobResponse",
    "QueryTypeEnum",
    "RAGChatRequest",
    "RAGChatResponse",
    "RefreshTokenRequest",
    "RegisterRequest",
    "ReindexRequest",
    "ReindexResponse",
    "ResendVerificationRequest",
    "ResetPasswordRequest",
    "RetrievedDocumentItem",
    "RoleResponse",
    "SearchFilterSchema",
    "SearchHistoryItemResponse",
    "SearchHistoryListResponse",
    "SearchRequest",
    "SearchResponse",
    "SearchResultItem",
    "SummarizeRequest",
    "SummarizeResponse",
    "SummaryTypeEnum",
    "TokenResponse",
    "TokenUsage",
    "TranslateRequest",
    "TranslateResponse",
    "UpdateProfileRequest",
    "UploadSessionResponse",
    "UserResponse",
    "VerifyEmailRequest",
]
