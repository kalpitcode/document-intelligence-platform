"""
Document Processing & OCR Controller Endpoints Module
======================================================

FastAPI REST controllers for triggering processing, status monitoring, and fetching
extracted content, chunks, tables, and images.

**Architectural Rationale:**
- Handlers contain no business logic; delegate to `DocumentProcessingService` and repositories.
- Enforces strict RBAC and document ownership checks (`owner_id` or `ADMIN`/`MANAGER` role).
- Standard envelope response model `APIResponse[T]`.
- OpenAPI examples and description for every controller handler.
"""

from __future__ import annotations

from typing import Annotated, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_async_session
from app.core.exceptions.base import ForbiddenError, NotFoundError
from app.core.storage import MinIOStorageProvider
from app.dependencies.auth import get_current_active_user
from app.models.user import UserModel
from app.repositories.document_repository import DocumentRepository
from app.repositories.processing_repository import (
    DocumentChunkRepository,
    DocumentContentRepository,
    ExtractedImageRepository,
    ExtractedTableRepository,
    ProcessingJobRepository,
)
from app.schemas.base import APIResponse
from app.schemas.processing import (
    DocumentChunkResponse,
    DocumentContentResponse,
    ExtractedImageResponse,
    ExtractedTableResponse,
    ProcessTriggerResponse,
    ProcessingJobResponse,
)
from app.services.document_processing_service import DocumentProcessingService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/documents", tags=["Document Processing & OCR"])


def get_processing_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> DocumentProcessingService:
    """Factory dependency instantiating DocumentProcessingService with session repositories."""
    doc_repo = DocumentRepository(session)
    content_repo = DocumentContentRepository(session)
    chunk_repo = DocumentChunkRepository(session)
    job_repo = ProcessingJobRepository(session)
    table_repo = ExtractedTableRepository(session)
    image_repo = ExtractedImageRepository(session)

    storage_service = StorageService(MinIOStorageProvider())

    return DocumentProcessingService(
        document_repo=doc_repo,
        content_repo=content_repo,
        chunk_repo=chunk_repo,
        job_repo=job_repo,
        table_repo=table_repo,
        image_repo=image_repo,
        storage_service=storage_service,
    )


async def _verify_document_access(
    document_id: uuid.UUID,
    user: UserModel,
    doc_repo: DocumentRepository,
) -> Any:
    """Helper verifying document existence and ownership/RBAC permissions."""
    doc = await doc_repo.get_by_id(document_id)
    if not doc or doc.deleted_at is not None:
        raise NotFoundError(f"Document with ID '{document_id}' not found")

    is_owner = doc.owner_id == user.id
    is_admin_or_manager = any(
        getattr(r, "name", str(r)) in ("ADMIN", "MANAGER", "ROLE_ADMIN", "ROLE_MANAGER")
        for r in (user.roles or [])
    )

    if not is_owner and not is_admin_or_manager:
        raise ForbiddenError("Insufficient permissions to access document processing outputs")

    return doc


@router.post(
    "/{document_id}/process",
    response_model=APIResponse[ProcessTriggerResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Async Document Processing",
    description="""
Initiates background OCR, text extraction, cleaning, table extraction, image extraction, and chunking pipeline.

**Pipeline Lifecycle:**
1. Validates document existence & ownership/RBAC permissions.
2. Initializes `ProcessingJobModel` state in `QUEUED`.
3. Executes processing task asynchronously.
""",
)
async def process_document_endpoint(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentProcessingService = Depends(get_processing_service),
) -> APIResponse[ProcessTriggerResponse]:
    """Trigger document processing endpoint."""
    await _verify_document_access(document_id, current_user, service.doc_repo)

    # Create job record
    job = await service.create_processing_job(document_id, worker_name="api.trigger")

    # In test/dev environment, run processing directly to update state synchronously or via Celery
    try:
        job = await service.process_document(document_id, job_id=job.id, worker_name="api.synchronous_execution")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {str(exc)}") from exc

    return APIResponse(
        success=True,
        message="Document processing completed successfully",
        data=ProcessTriggerResponse(
            job_id=job.id,
            document_id=document_id,
            status=job.status,
            message="Processing completed successfully",
        ),
    )


@router.get(
    "/{document_id}/content",
    response_model=APIResponse[DocumentContentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Processed Document Content",
    description="Retrieve extracted raw text, clean text, detected language code, word count, and character metrics.",
)
async def get_document_content_endpoint(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentProcessingService = Depends(get_processing_service),
) -> APIResponse[DocumentContentResponse]:
    """Get extracted text content endpoint."""
    await _verify_document_access(document_id, current_user, service.doc_repo)

    content = await service.content_repo.get_by_document_id(document_id)
    if not content:
        raise NotFoundError(f"Extracted content for document '{document_id}' not found. Please trigger processing first.")

    return APIResponse(
        success=True,
        message="Document content retrieved successfully",
        data=DocumentContentResponse.model_validate(content),
    )


@router.get(
    "/{document_id}/chunks",
    response_model=APIResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get Paginated Document Chunks",
    description="Retrieve sequential text chunks with character offsets, page number mappings, and token estimates.",
)
async def get_document_chunks_endpoint(
    document_id: uuid.UUID,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=200, description="Chunks per page")] = 50,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentProcessingService = Depends(get_processing_service),
) -> APIResponse[dict[str, Any]]:
    """Get document chunks endpoint."""
    await _verify_document_access(document_id, current_user, service.doc_repo)

    skip = (page - 1) * page_size
    items, total = await service.chunk_repo.get_chunks_by_document_id(document_id, skip=skip, limit=page_size)

    chunks_data = [DocumentChunkResponse.model_validate(c) for c in items]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return APIResponse(
        success=True,
        message="Document chunks retrieved successfully",
        data={
            "items": chunks_data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
    )


@router.get(
    "/{document_id}/tables",
    response_model=APIResponse[list[ExtractedTableResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get Extracted PDF Tables",
    description="Fetch structured tables extracted from document pages in JSON format.",
)
async def get_document_tables_endpoint(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentProcessingService = Depends(get_processing_service),
) -> APIResponse[list[ExtractedTableResponse]]:
    """Get document tables endpoint."""
    await _verify_document_access(document_id, current_user, service.doc_repo)

    tables = await service.table_repo.get_tables_by_document_id(document_id)
    table_data = [ExtractedTableResponse.model_validate(t) for t in tables]

    return APIResponse(
        success=True,
        message="Extracted document tables retrieved successfully",
        data=table_data,
    )


@router.get(
    "/{document_id}/images",
    response_model=APIResponse[list[ExtractedImageResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get Extracted Embedded Images",
    description="Fetch metadata and presigned download links for figures/images extracted from document pages.",
)
async def get_document_images_endpoint(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentProcessingService = Depends(get_processing_service),
) -> APIResponse[list[ExtractedImageResponse]]:
    """Get document images endpoint."""
    await _verify_document_access(document_id, current_user, service.doc_repo)

    images = await service.image_repo.get_images_by_document_id(document_id)

    image_data: list[ExtractedImageResponse] = []
    for img in images:
        download_url = None
        try:
            download_url = await service.storage_service.get_presigned_download_url(img.storage_path, expires_in=3600)
        except Exception:
            pass

        img_resp = ExtractedImageResponse(
            id=img.id,
            document_id=img.document_id,
            page_number=img.page_number,
            storage_path=img.storage_path,
            width=img.width,
            height=img.height,
            format=img.format,
            download_url=download_url,
            created_at=img.created_at,
        )
        image_data.append(img_resp)

    return APIResponse(
        success=True,
        message="Extracted document images retrieved successfully",
        data=image_data,
    )


@router.get(
    "/{document_id}/processing-status",
    response_model=APIResponse[ProcessingJobResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Processing Job Status",
    description="Fetch the latest processing job state, duration, retry count, and error message if failed.",
)
async def get_processing_status_endpoint(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentProcessingService = Depends(get_processing_service),
) -> APIResponse[ProcessingJobResponse]:
    """Get processing status endpoint."""
    await _verify_document_access(document_id, current_user, service.doc_repo)

    job = await service.job_repo.get_latest_job(document_id)
    if not job:
        raise NotFoundError(f"No processing jobs found for document '{document_id}'")

    return APIResponse(
        success=True,
        message="Processing job status retrieved successfully",
        data=ProcessingJobResponse.model_validate(job),
    )


@router.post(
    "/{document_id}/reprocess",
    response_model=APIResponse[ProcessTriggerResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Document Reprocessing",
    description="Purges old extracted content, chunks, tables, and images, and re-executes the processing pipeline.",
)
async def reprocess_document_endpoint(
    document_id: uuid.UUID,
    current_user: UserModel = Depends(get_current_active_user),
    service: DocumentProcessingService = Depends(get_processing_service),
) -> APIResponse[ProcessTriggerResponse]:
    """Trigger document reprocessing endpoint."""
    await _verify_document_access(document_id, current_user, service.doc_repo)

    job = await service.create_processing_job(document_id, worker_name="api.reprocess")

    try:
        job = await service.process_document(document_id, job_id=job.id, worker_name="api.reprocess_execution")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {str(exc)}") from exc

    return APIResponse(
        success=True,
        message="Document reprocessing completed successfully",
        data=ProcessTriggerResponse(
            job_id=job.id,
            document_id=document_id,
            status=job.status,
            message="Reprocessing completed successfully",
        ),
    )
