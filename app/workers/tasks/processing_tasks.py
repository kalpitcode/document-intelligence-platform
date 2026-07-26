"""
Celery Processing Tasks Module
===============================

Asynchronous Celery tasks for orchestrating document processing pipelines, OCR, text extraction,
table extraction, image extraction, language detection, content cleaning, and chunking.

**Architectural Rationale:**
- Retries with exponential backoff on transient errors.
- Runs async SQLAlchemy database operations in async event loops within Celery tasks.
"""

from __future__ import annotations

import asyncio
from typing import Any

from celery import shared_task
import structlog

from app.core.database.session import AsyncSessionLocal
from app.core.storage import MinIOStorageProvider
from app.repositories.document_repository import DocumentRepository
from app.repositories.processing_repository import (
    DocumentChunkRepository,
    DocumentContentRepository,
    ExtractedImageRepository,
    ExtractedTableRepository,
    ProcessingJobRepository,
)
from app.services.chunking_service import ChunkingService
from app.services.content_cleaning_service import ContentCleaningService
from app.services.document_processing_service import DocumentProcessingService
from app.services.image_extraction_service import ImageExtractionService
from app.services.language_detection_service import LanguageDetectionService
from app.services.ocr_service import OCRService
from app.services.storage_service import StorageService
from app.services.table_extraction_service import TableExtractionService
from app.services.text_extraction_service import TextExtractionService

logger = structlog.get_logger(__name__)


def _run_async(coro: Any) -> Any:
    """Helper executing an async coroutine synchronously inside Celery worker thread."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    name="app.workers.tasks.processing.process_document",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_document_task(self: Any, document_id: str, job_id: str | None = None) -> dict[str, Any]:
    """
    Primary background task executing full document processing pipeline.
    """
    logger.info("Executing process_document_task", document_id=document_id, job_id=job_id)

    async def _execute() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            doc_repo = DocumentRepository(session)
            content_repo = DocumentContentRepository(session)
            chunk_repo = DocumentChunkRepository(session)
            job_repo = ProcessingJobRepository(session)
            table_repo = ExtractedTableRepository(session)
            image_repo = ExtractedImageRepository(session)

            storage_service = StorageService(MinIOStorageProvider())
            processing_service = DocumentProcessingService(
                document_repo=doc_repo,
                content_repo=content_repo,
                chunk_repo=chunk_repo,
                job_repo=job_repo,
                table_repo=table_repo,
                image_repo=image_repo,
                storage_service=storage_service,
            )

            job = await processing_service.process_document(
                document_id=document_id,
                job_id=job_id,
                worker_name=self.request.hostname or "celery.worker",
            )
            await session.commit()
            return {"job_id": str(job.id), "status": job.status, "duration_ms": job.duration_ms}

    return _run_async(_execute())


@shared_task(name="app.workers.tasks.processing.extract_text", max_retries=3)
def extract_text_task(content_bytes: bytes, mime_type: str, filename: str) -> dict[str, Any]:
    """Sub-task extracting raw text from document payload."""
    service = TextExtractionService()
    res = service.extract_text(content_bytes, mime_type, filename)
    return {"raw_text": res.raw_text, "page_count": res.page_count}


@shared_task(name="app.workers.tasks.processing.extract_tables", max_retries=3)
def extract_tables_task(content_bytes: bytes, mime_type: str) -> list[dict[str, Any]]:
    """Sub-task extracting tables from document payload."""
    service = TableExtractionService()
    tables = service.extract_tables(content_bytes, mime_type)
    return [t.to_dict() for t in tables]


@shared_task(name="app.workers.tasks.processing.extract_images", max_retries=3)
def extract_images_task(document_id: str, content_bytes: bytes, mime_type: str) -> list[dict[str, Any]]:
    """Sub-task extracting embedded images."""
    storage_service = StorageService(MinIOStorageProvider())
    service = ImageExtractionService(storage_service)
    imgs = _run_async(service.extract_images(document_id, content_bytes, mime_type))
    return [
        {
            "page_number": img.page_number,
            "storage_path": img.storage_path,
            "width": img.width,
            "height": img.height,
            "format": img.format,
        }
        for img in imgs
    ]


@shared_task(name="app.workers.tasks.processing.detect_language")
def detect_language_task(text: str) -> str:
    """Sub-task identifying primary ISO language code."""
    service = LanguageDetectionService()
    return service.detect_language(text)


@shared_task(name="app.workers.tasks.processing.clean_content")
def clean_content_task(raw_text: str) -> str:
    """Sub-task performing text cleaning and Unicode normalization."""
    service = ContentCleaningService()
    return service.clean_text(raw_text)


@shared_task(name="app.workers.tasks.processing.create_chunks")
def create_chunks_task(document_id: str, clean_text: str) -> list[dict[str, Any]]:
    """Sub-task splitting text into deterministic sequential chunks."""
    service = ChunkingService()
    chunks = service.create_chunks(document_id, clean_text)
    return [
        {
            "document_id": str(c.document_id),
            "chunk_index": c.chunk_index,
            "content": c.content,
            "page_number": c.page_number,
            "start_offset": c.start_offset,
            "end_offset": c.end_offset,
            "token_estimate": c.token_estimate,
        }
        for c in chunks
    ]
