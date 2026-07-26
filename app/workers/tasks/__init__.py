"""
Tasks Package
=============

Exported Celery worker tasks for document processing, knowledge indexing, RAG, and AI features.
"""

from __future__ import annotations

from app.workers.tasks.ai_tasks import (
    analyze_document_task,
    extract_entities_task,
    generate_summary_task,
    retry_failed_ai_jobs_task,
    run_classification_task,
    translate_document_task,
)
from app.workers.tasks.knowledge_tasks import (
    delete_document_embeddings_task,
    index_document_embeddings_task,
)

__all__ = [
    "analyze_document_task",
    "delete_document_embeddings_task",
    "extract_entities_task",
    "generate_summary_task",
    "index_document_embeddings_task",
    "retry_failed_ai_jobs_task",
    "run_classification_task",
    "translate_document_task",
]
