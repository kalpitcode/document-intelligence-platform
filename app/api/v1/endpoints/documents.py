"""
Document Endpoints Module
==========================

FastAPI API controllers for enterprise document upload, retrieval, versioning, download presigning,
soft deletion, and metadata update operations.

**Architectural Rationale:**
- Handlers contain no business logic; delegate entirely to `DocumentService`.
- Standard envelope response model `APIResponse[T]`.
- Full OpenAPI documentation with description, security requirements, and examples.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_async_session
from app.core.storage import MinIOStorageProvider
from app.dependencies.auth import get_current_active_user
from app.models.document import DocumentStatus, Visibility
from app.models.user import UserModel
from app.repositories.document_repository import DocumentRepository
from app.repositories.metadata_repository import MetadataRepository
from app.repositories.upload_repository import UploadRepository
from app.repositories.version_repository import VersionRepository
from app.schemas.base import APIResponse
from app.schemas.document import (
    DocumentDownloadResponse,
    DocumentResponse,
    DocumentUpdate,
    DocumentVersionResponse,
)
from app.services.checksum_service import ChecksumService
from app.services.document_service import DocumentService
from app.services.metadata_service import MetadataService
from app.services.storage_service import StorageService
from app.services.upload_service import UploadService
from app.services.validation_service import ValidationService
from app.services.version_service import VersionService

router = APIRouter(prefix="/documents", tags=["Documents"])


def get_document_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> DocumentService:
    """Factory dependency instantiating DocumentService and its required components."""
    doc_repo = DocumentRepository(session)
    version_repo = VersionRepository(session)
    metadata_repo = MetadataRepository(session)
    upload_repo = UploadRepository(session)

    storage_provider = MinIOStorageProvider()
    storage_service = StorageService(storage_provider)
    validation_service = ValidationService()
    checksum_service = ChecksumService()
    metadata_service = MetadataService(metadata_repo)
    version_service = VersionService(version_repo)
    upload_service = UploadService(upload_repo)

    return DocumentService(
        document_repo=doc_repo,
        storage_service=storage_service,
        validation_service=validation_service,
        checksum_service=checksum_service,
        metadata_service=metadata_service,
        version_service=version_service,
        upload_service=upload_service,
    )


@router.post(
    "/upload",
    response_model=APIResponse[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Managed Document",
    description="""
Upload a document file to the enterprise document storage system.

**Upload Pipeline Execution:**
1. Validates file extension, MIME type, security rules, and 100MB max limit.
2. Computes stream SHA-256 digest for deduplication.
3. Generates server-side UUID storage path.
4. Uploads object content to MinIO storage bucket.
5. Persists Document, Metadata, and Version 1 records.
6. Publishes `DocumentUploaded` domain event.
""",
)
async def upload_document(
    file: Annotated[UploadFile, File(description="Document binary file (PDF, DOCX, TXT, CSV, XLSX, PNG, JPEG)")],
    visibility: Annotated[str, Form(description="Document visibility: Private, Shared, Organization, Public")] = Visibility.PRIVATE.value,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[DocumentResponse]:
    """Upload new document controller endpoint."""
    content = await file.read()
    doc = await service.upload_document(
        current_user=current_user,
        filename=file.filename or "file.bin",
        content=content,
        declared_mime=file.content_type,
        visibility=visibility,
    )
    return APIResponse(
        success=True,
        message="Document uploaded successfully",
        data=DocumentResponse.model_validate(doc),
    )


@router.get(
    "/{document_id}",
    response_model=APIResponse[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Document Details",
    description="Retrieve metadata, versions, and tags for a specific document by ID.",
)
async def get_document(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[DocumentResponse]:
    """Get single document details endpoint."""
    doc = await service.get_document(document_id, current_user)
    return APIResponse(
        success=True,
        message="Document details retrieved successfully",
        data=DocumentResponse.model_validate(doc),
    )


@router.get(
    "",
    response_model=APIResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List & Filter Documents",
    description="List documents with multi-field filtering, sorting, and pagination.",
)
async def list_documents(
    filename: Annotated[str | None, Query(description="Filter by filename substring")] = None,
    doc_status: Annotated[str | None, Query(alias="status", description="Filter by status")] = None,
    visibility: Annotated[str | None, Query(description="Filter by visibility")] = None,
    mime_type: Annotated[str | None, Query(description="Filter by MIME type")] = None,
    date_from: Annotated[datetime | None, Query(description="Filter created on/after UTC date")] = None,
    date_to: Annotated[datetime | None, Query(description="Filter created on/before UTC date")] = None,
    sort_by: Annotated[str, Query(description="Sort field: created_at, updated_at, filename, size")] = "created_at",
    sort_order: Annotated[str, Query(description="Sort order: asc or desc")] = "desc",
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[dict[str, Any]]:
    """List documents with pagination controller endpoint."""
    skip = (page - 1) * page_size
    items, total = await service.list_documents(
        current_user=current_user,
        filename=filename,
        status=doc_status,
        visibility=visibility,
        mime_type=mime_type,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=page_size,
    )
    docs_data = [DocumentResponse.model_validate(doc) for doc in items]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return APIResponse(
        success=True,
        message="Documents retrieved successfully",
        data={
            "items": docs_data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
    )


@router.get(
    "/{document_id}/download",
    response_model=APIResponse[DocumentDownloadResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Presigned Document Download URL",
    description="Generate a secure presigned download link for the requested document.",
)
async def download_document(
    document_id: uuid.UUID,
    expires_in: Annotated[int, Query(ge=60, le=86400, description="URL validity in seconds")] = 3600,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[DocumentDownloadResponse]:
    """Get presigned download URL controller endpoint."""
    doc = await service.get_document(document_id, current_user)
    download_url = await service.get_download_url(document_id, current_user, expires_in)

    return APIResponse(
        success=True,
        message="Presigned download URL generated successfully",
        data=DocumentDownloadResponse(
            document_id=doc.id,
            original_filename=doc.original_filename,
            download_url=download_url,
            expires_in_seconds=expires_in,
        ),
    )


@router.delete(
    "/{document_id}",
    response_model=APIResponse[dict[str, bool]],
    status_code=status.HTTP_200_OK,
    summary="Delete Document",
    description="Soft delete a document and update its status to DELETED.",
)
async def delete_document(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[dict[str, bool]]:
    """Soft delete document controller endpoint."""
    success = await service.delete_document(document_id, current_user)
    return APIResponse(
        success=True,
        message="Document soft-deleted successfully",
        data={"deleted": success},
    )


@router.patch(
    "/{document_id}",
    response_model=APIResponse[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Document Metadata / Visibility",
    description="Update metadata, visibility level, or lifecycle status of a document.",
)
async def update_document(
    document_id: uuid.UUID,
    body: DocumentUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[DocumentResponse]:
    """Update document attributes controller endpoint."""
    doc = await service.get_document(document_id, current_user)

    update_fields: dict[str, Any] = {}
    if body.visibility is not None:
        update_fields["visibility"] = body.visibility.value if isinstance(body.visibility, Visibility) else body.visibility
    if body.status is not None:
        update_fields["status"] = body.status.value if isinstance(body.status, DocumentStatus) else body.status

    if update_fields:
        doc = await service.doc_repo.update(doc, **update_fields)

    if body.custom_metadata is not None:
        await service.metadata_service.update_custom_metadata(doc.id, body.custom_metadata)
        doc = await service.doc_repo.get_by_id_with_relations(doc.id) or doc

    return APIResponse(
        success=True,
        message="Document updated successfully",
        data=DocumentResponse.model_validate(doc),
    )


@router.post(
    "/{document_id}/versions",
    response_model=APIResponse[DocumentVersionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload New Document Version",
    description="Upload a new file version for an existing document.",
)
async def upload_document_version(
    document_id: uuid.UUID,
    file: Annotated[UploadFile, File(description="New version file content")],
    change_notes: Annotated[str | None, Form(description="Version change notes or release description")] = None,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[DocumentVersionResponse]:
    """Upload new document version controller endpoint."""
    content = await file.read()
    version = await service.create_new_version(
        document_id=document_id,
        current_user=current_user,
        filename=file.filename or "file.bin",
        content=content,
        change_notes=change_notes,
    )
    return APIResponse(
        success=True,
        message=f"Document version {version.version_number} uploaded successfully",
        data=DocumentVersionResponse.model_validate(version),
    )


@router.get(
    "/{document_id}/versions",
    response_model=APIResponse[list[DocumentVersionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Document Version History",
    description="Fetch all historic version records for a specific document.",
)
async def list_document_versions(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentService = Depends(get_document_service),
) -> APIResponse[list[DocumentVersionResponse]]:
    """List document versions controller endpoint."""
    doc = await service.get_document(document_id, current_user)
    versions = await service.version_service.get_version_history(doc.id)
    versions_data = [DocumentVersionResponse.model_validate(v) for v in versions]

    return APIResponse(
        success=True,
        message="Document version history retrieved successfully",
        data=versions_data,
    )
