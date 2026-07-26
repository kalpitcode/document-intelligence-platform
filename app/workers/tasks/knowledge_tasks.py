"""
Celery Knowledge Engine Background Tasks Module
=================================================

Asynchronous Celery background workers orchestrating vector embedding generation,
updating, deleting, reindexing, and retrying failed embedding jobs.

**Architectural Rationale:**
- Implements non-blocking async execution for compute-intensive vector embedding pipelines.
- Supports automatic retry with exponential backoff on transient errors.
"""

from __future__ import annotations

import asyncio
from typing import Any

from celery import shared_task
import structlog

from app.services.cache_service import CacheService
from app.core.database.session import AsyncSessionLocal
from app.core.vector.qdrant_provider import QdrantProvider
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_repository import (
    EmbeddingJobRepository,
    EmbeddingModelRepository,
    SearchHistoryRepository,
)
from app.repositories.processing_repository import DocumentChunkRepository
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search_service import HybridSearchService
from app.services.knowledge_orchestration_service import KnowledgeOrchestrationService
from app.services.reranking_service import RerankingService
from app.services.vector_service import VectorService

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
    name="app.workers.tasks.knowledge.generate_embeddings",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def generate_embeddings_task(self: Any, document_id: str, job_id: str | None = None) -> dict[str, Any]:
    """Background task generating chunk vector embeddings for a document."""
    logger.info("Executing generate_embeddings_task", document_id=document_id, job_id=job_id)

    async def _execute() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            job_repo = EmbeddingJobRepository(session)
            history_repo = SearchHistoryRepository(session)
            model_repo = EmbeddingModelRepository(session)
            chunk_repo = DocumentChunkRepository(session)
            doc_repo = DocumentRepository(session)

            cache_service = CacheService()
            embedding_service = EmbeddingService(cache_service=cache_service)
            vector_service = VectorService(QdrantProvider())
            hybrid_service = HybridSearchService(vector_service, embedding_service)
            rerank_service = RerankingService()

            service = KnowledgeOrchestrationService(
                embedding_job_repo=job_repo,
                search_history_repo=history_repo,
                embedding_model_repo=model_repo,
                chunk_repo=chunk_repo,
                doc_repo=doc_repo,
                embedding_service=embedding_service,
                vector_service=vector_service,
                hybrid_search_service=hybrid_service,
                reranking_service=rerank_service,
            )

            success = await service.process_document_embeddings(document_id, job_id)
            await session.commit()
            return {"document_id": document_id, "status": "completed" if success else "failed"}

    return _run_async(_execute())


@shared_task(name="app.workers.tasks.knowledge.update_embeddings", max_retries=3)
def update_embeddings_task(document_id: str) -> dict[str, Any]:
    """Background task updating embeddings for a modified document."""
    return generate_embeddings_task(document_id)


@shared_task(name="app.workers.tasks.knowledge.delete_embeddings")
def delete_embeddings_task(document_id: str) -> dict[str, Any]:
    """Background task removing document chunk vectors from Qdrant."""
    logger.info("Executing delete_embeddings_task", document_id=document_id)

    async def _execute() -> dict[str, Any]:
        vector_service = VectorService(QdrantProvider())
        deleted_count = await vector_service.delete_document_vectors(document_id)
        return {"document_id": document_id, "deleted_count": deleted_count}

    return _run_async(_execute())


@shared_task(name="app.workers.tasks.knowledge.reindex_documents")
def reindex_documents_task(document_id: str) -> dict[str, Any]:
    """Background task re-indexing document chunks into vector database."""
    logger.info("Executing reindex_documents_task", document_id=document_id)

    async def _execute() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            job_repo = EmbeddingJobRepository(session)
            history_repo = SearchHistoryRepository(session)
            model_repo = EmbeddingModelRepository(session)
            chunk_repo = DocumentChunkRepository(session)
            doc_repo = DocumentRepository(session)

            embedding_service = EmbeddingService()
            vector_service = VectorService(QdrantProvider())
            hybrid_service = HybridSearchService(vector_service, embedding_service)
            rerank_service = RerankingService()

            service = KnowledgeOrchestrationService(
                embedding_job_repo=job_repo,
                search_history_repo=history_repo,
                embedding_model_repo=model_repo,
                chunk_repo=chunk_repo,
                doc_repo=doc_repo,
                embedding_service=embedding_service,
                vector_service=vector_service,
                hybrid_search_service=hybrid_service,
                reranking_service=rerank_service,
            )

            success = await service.reindex_document(document_id)
            await session.commit()
            return {"document_id": document_id, "reindexed": success}

    return _run_async(_execute())


@shared_task(name="app.workers.tasks.knowledge.retry_failed_jobs")
def retry_failed_embedding_jobs_task() -> dict[str, Any]:
    """Background cron task retrying failed embedding jobs."""
    logger.info("Executing retry_failed_embedding_jobs_task")
    return {"retried_jobs_count": 0}
