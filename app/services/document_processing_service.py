"""
Document Processing Master Orchestrator Service Module
=========================================================

Orchestrates the entire asynchronous OCR, text extraction, cleaning, language detection,
table extraction, image extraction, and chunking pipeline.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID (Single Responsibility per sub-service).
- Manages ProcessingJob status transitions (QUEUED -> RUNNING -> COMPLETED / FAILED).
- Publishes Domain Events and records compliance Audit logs.
- Safe rollback / cleanup on reprocessing or failure.
"""

from __future__ import annotations

from datetime import UTC, datetime
import time
import uuid
from typing import Any

import structlog

from app.core.events import (
    DocumentChunkCreated,
    DocumentProcessingCompleted,
    DocumentProcessingFailed,
    DocumentProcessingStarted,
    EventBus,
    ImageExtracted,
    TableExtracted,
)
from app.core.exceptions.base import NotFoundError, ProcessingError
from app.models.document import DocumentModel, DocumentStatus
from app.models.processing import ProcessingJobModel, ProcessingStatus
from app.repositories.document_repository import DocumentRepository
from app.repositories.processing_repository import (
    DocumentChunkRepository,
    DocumentContentRepository,
    ExtractedImageRepository,
    ExtractedTableRepository,
    ProcessingJobRepository,
)
from app.services.audit_service import AuditService
from app.services.chunking_service import ChunkingService
from app.services.content_cleaning_service import ContentCleaningService
from app.services.image_extraction_service import ImageExtractionService
from app.services.language_detection_service import LanguageDetectionService
from app.services.storage_service import StorageService
from app.services.table_extraction_service import TableExtractionService
from app.services.text_extraction_service import TextExtractionService

logger = structlog.get_logger(__name__)


class DocumentProcessingService:
    """Master orchestrator service processing document assets."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        content_repo: DocumentContentRepository,
        chunk_repo: DocumentChunkRepository,
        job_repo: ProcessingJobRepository,
        table_repo: ExtractedTableRepository,
        image_repo: ExtractedImageRepository,
        storage_service: StorageService,
        text_extraction_service: TextExtractionService | None = None,
        content_cleaning_service: ContentCleaningService | None = None,
        language_detection_service: LanguageDetectionService | None = None,
        table_extraction_service: TableExtractionService | None = None,
        image_extraction_service: ImageExtractionService | None = None,
        chunking_service: ChunkingService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.doc_repo = document_repo
        self.content_repo = content_repo
        self.chunk_repo = chunk_repo
        self.job_repo = job_repo
        self.table_repo = table_repo
        self.image_repo = image_repo
        self.storage_service = storage_service

        self.text_extraction_service = text_extraction_service or TextExtractionService()
        self.content_cleaning_service = content_cleaning_service or ContentCleaningService()
        self.language_detection_service = language_detection_service or LanguageDetectionService()
        self.table_extraction_service = table_extraction_service or TableExtractionService()
        self.image_extraction_service = image_extraction_service or ImageExtractionService(storage_service)
        self.chunking_service = chunking_service or ChunkingService()
        self.audit_service = audit_service

    async def create_processing_job(
        self,
        document_id: uuid.UUID | str,
        worker_name: str = "celery.worker",
    ) -> ProcessingJobModel:
        """Create a new processing job in QUEUED status."""
        doc_uuid = uuid.UUID(str(document_id)) if isinstance(document_id, str) else document_id
        return await self.job_repo.create(
            document_id=doc_uuid,
            status=ProcessingStatus.QUEUED.value,
            worker_name=worker_name,
            retry_count=0,
        )

    async def process_document(
        self,
        document_id: uuid.UUID | str,
        job_id: uuid.UUID | str | None = None,
        worker_name: str = "celery.worker",
    ) -> ProcessingJobModel:
        """
        Execute full asynchronous document processing pipeline.

        Pipeline Steps:
        1. Fetch document record & update status to PROCESSING.
        2. Create / retrieve ProcessingJob and transition to RUNNING.
        3. Download binary asset from StorageService.
        4. Text Extraction (PyMuPDF / OCR).
        5. Content Cleaning & Unicode normalization.
        6. Language Detection.
        7. Table Extraction (pdfplumber).
        8. Image Extraction (PyMuPDF -> Storage).
        9. Deterministic Chunking.
        10. Save all results & transition job to COMPLETED.
        """
        doc_uuid = uuid.UUID(str(document_id)) if isinstance(document_id, str) else document_id
        start_time = time.time()

        # Fetch document
        doc = await self.doc_repo.get_by_id(doc_uuid)
        if not doc or doc.deleted_at is not None:
            raise NotFoundError(f"Document with ID '{doc_uuid}' not found")

        # Update document status
        await self.doc_repo.update(doc, status=DocumentStatus.PROCESSING.value)

        # Get or create job record
        if job_id:
            job = await self.job_repo.get_by_id(uuid.UUID(str(job_id)))
        else:
            job = await self.create_processing_job(doc_uuid, worker_name=worker_name)

        if not job:
            job = await self.job_repo.create(
                document_id=doc_uuid,
                status=ProcessingStatus.QUEUED.value,
                worker_name=worker_name,
            )

        # Mark job RUNNING
        job = await self.job_repo.update(
            job,
            status=ProcessingStatus.RUNNING.value,
            started_at=datetime.now(UTC),
            worker_name=worker_name,
        )

        EventBus.publish(
            DocumentProcessingStarted(
                document_id=str(doc_uuid),
                job_id=str(job.id),
                worker_name=worker_name,
            )
        )

        if self.audit_service:
            await self.audit_service.log_event(
                action="OCR Started",
                target_resource=f"document:{doc_uuid}",
                details={"job_id": str(job.id), "filename": doc.original_filename},
            )

        try:
            # Clear old records if reprocessing
            await self.chunk_repo.delete_by_document_id(doc_uuid)
            await self.table_repo.delete_by_document_id(doc_uuid)
            await self.image_repo.delete_by_document_id(doc_uuid)

            # Download document content
            file_bytes = await self.storage_service.get_file_content(doc.storage_path)

            # Step 1: Text Extraction
            extraction_res = self.text_extraction_service.extract_text(
                content=file_bytes,
                mime_type=doc.mime_type,
                filename=doc.original_filename,
            )

            # Step 2: Content Cleaning
            clean_text = self.content_cleaning_service.clean_text(extraction_res.raw_text)

            # Step 3: Language Detection
            lang_code = self.language_detection_service.detect_language(clean_text)

            # Save / update DocumentContentModel
            existing_content = await self.content_repo.get_by_document_id(doc_uuid)
            word_count = len(clean_text.split())
            char_count = len(clean_text)
            page_count = max(1, extraction_res.page_count)

            if existing_content:
                await self.content_repo.update(
                    existing_content,
                    raw_text=extraction_res.raw_text,
                    clean_text=clean_text,
                    language=lang_code,
                    character_count=char_count,
                    word_count=word_count,
                    page_count=page_count,
                    processing_status=ProcessingStatus.COMPLETED.value,
                )
            else:
                await self.content_repo.create(
                    document_id=doc_uuid,
                    raw_text=extraction_res.raw_text,
                    clean_text=clean_text,
                    language=lang_code,
                    character_count=char_count,
                    word_count=word_count,
                    page_count=page_count,
                    processing_status=ProcessingStatus.COMPLETED.value,
                )

            # Step 4: Table Extraction
            extracted_tables = self.table_extraction_service.extract_tables(
                content=file_bytes,
                mime_type=doc.mime_type,
            )
            for tbl in extracted_tables:
                tbl_model = await self.table_repo.create(
                    document_id=doc_uuid,
                    page_number=tbl.page_number,
                    table_index=tbl.table_index,
                    table_json=tbl.to_dict(),
                )
                EventBus.publish(
                    TableExtracted(
                        document_id=str(doc_uuid),
                        table_id=str(tbl_model.id),
                        page_number=tbl.page_number,
                        row_count=len(tbl.rows),
                    )
                )

            if extracted_tables and self.audit_service:
                await self.audit_service.log_event(
                    action="Table Extraction",
                    target_resource=f"document:{doc_uuid}",
                    details={"table_count": len(extracted_tables)},
                )

            # Step 5: Image Extraction
            extracted_images = await self.image_extraction_service.extract_images(
                document_id=doc_uuid,
                content=file_bytes,
                mime_type=doc.mime_type,
            )
            for img in extracted_images:
                img_model = await self.image_repo.create(
                    document_id=doc_uuid,
                    page_number=img.page_number,
                    storage_path=img.storage_path,
                    width=img.width,
                    height=img.height,
                    format=img.format,
                )
                EventBus.publish(
                    ImageExtracted(
                        document_id=str(doc_uuid),
                        image_id=str(img_model.id),
                        page_number=img.page_number,
                        storage_path=img.storage_path,
                    )
                )

            if extracted_images and self.audit_service:
                await self.audit_service.log_event(
                    action="Image Extraction",
                    target_resource=f"document:{doc_uuid}",
                    details={"image_count": len(extracted_images)},
                )

            # Step 6: Chunking
            chunk_payloads = self.chunking_service.create_chunks(
                document_id=doc_uuid,
                clean_text=clean_text,
            )
            for chunk_p in chunk_payloads:
                chk_model = await self.chunk_repo.create(
                    document_id=doc_uuid,
                    chunk_index=chunk_p.chunk_index,
                    content=chunk_p.content,
                    page_number=chunk_p.page_number,
                    start_offset=chunk_p.start_offset,
                    end_offset=chunk_p.end_offset,
                    token_estimate=chunk_p.token_estimate,
                )
                EventBus.publish(
                    DocumentChunkCreated(
                        document_id=str(doc_uuid),
                        chunk_id=str(chk_model.id),
                        chunk_index=chunk_p.chunk_index,
                        token_estimate=chunk_p.token_estimate,
                    )
                )

            if self.audit_service:
                await self.audit_service.log_event(
                    action="Chunk Generation",
                    target_resource=f"document:{doc_uuid}",
                    details={"chunk_count": len(chunk_payloads)},
                )

            # Finalize Job & Document Status
            duration_ms = int((time.time() - start_time) * 1000)
            job = await self.job_repo.update(
                job,
                status=ProcessingStatus.COMPLETED.value,
                completed_at=datetime.now(UTC),
                duration_ms=duration_ms,
            )

            await self.doc_repo.update(doc, status=DocumentStatus.UPLOADED.value)

            EventBus.publish(
                DocumentProcessingCompleted(
                    document_id=str(doc_uuid),
                    job_id=str(job.id),
                    word_count=word_count,
                    chunk_count=len(chunk_payloads),
                    table_count=len(extracted_tables),
                    image_count=len(extracted_images),
                )
            )

            if self.audit_service:
                await self.audit_service.log_event(
                    action="OCR Completed",
                    target_resource=f"document:{doc_uuid}",
                    details={"duration_ms": duration_ms, "word_count": word_count},
                )

            return job

        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            err_msg = str(exc)
            logger.error("Document processing failed", document_id=str(doc_uuid), error=err_msg)

            job = await self.job_repo.update(
                job,
                status=ProcessingStatus.FAILED.value,
                completed_at=datetime.now(UTC),
                duration_ms=duration_ms,
                error_message=err_msg,
            )
            await self.doc_repo.update(doc, status=DocumentStatus.FAILED.value)

            EventBus.publish(
                DocumentProcessingFailed(
                    document_id=str(doc_uuid),
                    job_id=str(job.id),
                    error_message=err_msg,
                )
            )

            if self.audit_service:
                await self.audit_service.log_event(
                    action="OCR Failed",
                    target_resource=f"document:{doc_uuid}",
                    status="FAILURE",
                    details={"error": err_msg},
                )

            raise ProcessingError(f"Document processing failed: {err_msg}") from exc
