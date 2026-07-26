"""
Background Task Stubs Module
==============================

Defines lightweight placeholder stubs for future background processing tasks.

**Architectural Rationale:**
- OCR, AI, Thumbnail, and Virus Scanning are out of scope for Milestone 3.
- Stubs allow the upload pipeline to enqueue job events/stubs without breaking workflow modularity.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def ocr_task_stub(document_id: str) -> dict[str, Any]:
    """Stub placeholder for future OCR processing task."""
    logger.info("CR_TASK_STUB: Queueing OCR job for document %s", document_id)
    return {"status": "QUEUED", "task": "OCR", "document_id": document_id}


def thumbnail_task_stub(document_id: str) -> dict[str, Any]:
    """Stub placeholder for future thumbnail generation task."""
    logger.info("THUMBNAIL_TASK_STUB: Queueing thumbnail job for document %s", document_id)
    return {"status": "QUEUED", "task": "THUMBNAIL", "document_id": document_id}


def embedding_task_stub(document_id: str) -> dict[str, Any]:
    """Stub placeholder for future AI vector embedding generation task."""
    logger.info("EMBEDDING_TASK_STUB: Queueing embedding job for document %s", document_id)
    return {"status": "QUEUED", "task": "EMBEDDING", "document_id": document_id}


def virus_scan_task_stub(document_id: str) -> dict[str, Any]:
    """Stub placeholder for future virus scan task."""
    logger.info("VIRUS_SCAN_TASK_STUB: Queueing virus scan for document %s", document_id)
    return {"status": "QUEUED", "task": "VIRUS_SCAN", "document_id": document_id}


def metadata_extraction_task_stub(document_id: str) -> dict[str, Any]:
    """Stub placeholder for future metadata extraction task."""
    logger.info("METADATA_EXTRACTION_STUB: Queueing metadata extraction for document %s", document_id)
    return {"status": "QUEUED", "task": "METADATA_EXTRACTION", "document_id": document_id}
