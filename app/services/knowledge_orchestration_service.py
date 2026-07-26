"""
Knowledge Engine Master Orchestrator Service Module
===================================================

Master domain service driving document chunk vector embedding jobs, vector indexing in Qdrant,
hybrid semantic search execution, cross-encoder re-ranking, search history auditing,
and domain event publishing.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Coordinates EmbeddingJobRepository, SearchHistoryRepository, EmbeddingModelRepository,
  DocumentChunkRepository, DocumentRepository, EmbeddingService, VectorService, HybridSearchService, RerankingService.
- Emits domain events (`EmbeddingStarted`, `EmbeddingCompleted`, `EmbeddingFailed`, `DocumentIndexed`, `DocumentRemovedFromIndex`).
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
import time
from typing import Any, Sequence
import uuid

from app.core.events import (
    DocumentIndexed,
    DocumentRemovedFromIndex,
    EmbeddingCompleted,
    EmbeddingFailed,
    EmbeddingStarted,
    EventBus,
)
from app.models.knowledge import EmbeddingJobModel, EmbeddingJobStatus, EmbeddingModelModel, SearchHistoryModel
from app.models.user import UserModel
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_repository import (
    EmbeddingJobRepository,
    EmbeddingModelRepository,
    SearchHistoryRepository,
)
from app.repositories.processing_repository import DocumentChunkRepository
from app.schemas.knowledge import SearchResponse, SearchResultItem
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search_service import HybridSearchService
from app.services.reranking_service import RerankingService
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)


class KnowledgeOrchestrationService:
    """
    Master Knowledge Engine Service.

    Orchestrates document chunk embedding generation, vector indexing, hybrid search,
    candidate re-ranking, and search query auditing.
    """

    def __init__(
        self,
        embedding_job_repo: EmbeddingJobRepository,
        search_history_repo: SearchHistoryRepository,
        embedding_model_repo: EmbeddingModelRepository,
        chunk_repo: DocumentChunkRepository,
        doc_repo: DocumentRepository,
        embedding_service: EmbeddingService,
        vector_service: VectorService,
        hybrid_search_service: HybridSearchService,
        reranking_service: RerankingService,
    ) -> None:
        self.job_repo = embedding_job_repo
        self.history_repo = search_history_repo
        self.model_repo = embedding_model_repo
        self.chunk_repo = chunk_repo
        self.doc_repo = doc_repo
        self.embedding_service = embedding_service
        self.vector_service = vector_service
        self.hybrid_search_service = hybrid_search_service
        self.reranking_service = reranking_service

    async def create_embedding_job(self, document_id: uuid.UUID | str) -> EmbeddingJobModel:
        """Initialize a new embedding job record."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        job = await self.job_repo.create(
            document_id=document_id,
            status=EmbeddingJobStatus.QUEUED.value,
            embedding_model=self.embedding_service.model_name,
        )
        return job

    async def process_document_embeddings(
        self,
        document_id: uuid.UUID | str,
        job_id: uuid.UUID | str | None = None,
    ) -> bool:
        """
        Execute embedding pipeline for document:
        Fetch chunks -> Generate vectors -> Upsert Qdrant -> Update Job -> Publish Events
        """
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        start_time = time.time()

        # Fetch job or create
        job = None
        if job_id:
            job = await self.job_repo.get_by_id(job_id)
        if not job:
            job = await self.job_repo.get_latest_job(document_id)
        if not job:
            job = await self.create_embedding_job(document_id)

        # Update status to RUNNING
        await self.job_repo.update(
            job,
            status=EmbeddingJobStatus.RUNNING.value,
            started_at=datetime.now(UTC),
        )

        EventBus.publish(
            EmbeddingStarted(
                document_id=str(document_id),
                job_id=str(job.id),
                embedding_model=self.embedding_service.model_name,
            )
        )

        try:
            # 1. Fetch document and chunks
            doc = await self.doc_repo.get_by_id_with_relations(document_id)
            if not doc:
                raise ValueError(f"Document with ID '{document_id}' not found")

            chunks, total_chunks = await self.chunk_repo.get_chunks_by_document_id(document_id, limit=1000)
            if not chunks:
                logger.warning("No text chunks found for document '%s' during embedding generation", document_id)
                duration_ms = int((time.time() - start_time) * 1000)
                await self.job_repo.update(
                    job,
                    status=EmbeddingJobStatus.COMPLETED.value,
                    completed_at=datetime.now(UTC),
                    duration_ms=duration_ms,
                )
                return True

            # 2. Extract texts and generate embeddings
            chunk_texts = [c.content for c in chunks]
            vectors = await self.embedding_service.generate_batch_embeddings(chunk_texts)

            # 3. Build Qdrant points
            points = []
            for chunk, vec in zip(chunks, vectors):
                points.append({
                    "id": str(chunk.id),
                    "vector": vec,
                    "payload": {
                        "chunk_id": str(chunk.id),
                        "document_id": str(doc.id),
                        "owner_id": str(doc.owner_id),
                        "chunk_index": chunk.chunk_index,
                        "page_number": getattr(chunk, "page_number", 1) or 1,
                        "text_snippet": chunk.content,
                        "token_estimate": chunk.token_estimate,
                        "visibility": doc.visibility if isinstance(doc.visibility, str) else str(doc.visibility),
                        "mime_type": doc.mime_type if isinstance(doc.mime_type, str) else str(doc.mime_type),
                        "original_filename": doc.original_filename if isinstance(doc.original_filename, str) else str(doc.original_filename),
                        "language": getattr(doc.content_record, "language", "en") if getattr(doc, "content_record", None) else "en",
                    },
                })

            # 4. Upsert vectors into Qdrant
            await self.vector_service.insert_chunk_vectors(points)

            # 5. Mark Job COMPLETED
            duration_ms = int((time.time() - start_time) * 1000)
            await self.job_repo.update(
                job,
                status=EmbeddingJobStatus.COMPLETED.value,
                completed_at=datetime.now(UTC),
                duration_ms=duration_ms,
            )

            # 6. Publish completion events
            EventBus.publish(
                EmbeddingCompleted(
                    document_id=str(document_id),
                    job_id=str(job.id),
                    chunk_count=len(chunks),
                    duration_ms=duration_ms,
                )
            )

            EventBus.publish(
                DocumentIndexed(
                    document_id=str(document_id),
                    indexed_chunks=len(chunks),
                )
            )

            return True

        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            error_str = str(exc)
            logger.error("Embedding generation job failed for document '%s': %s", document_id, error_str)

            await self.job_repo.update(
                job,
                status=EmbeddingJobStatus.FAILED.value,
                completed_at=datetime.now(UTC),
                duration_ms=duration_ms,
                error_message=error_str,
                retry_count=job.retry_count + 1,
            )

            EventBus.publish(
                EmbeddingFailed(
                    document_id=str(document_id),
                    job_id=str(job.id),
                    reason=error_str,
                )
            )
            raise

    async def search_knowledge_base(
        self,
        query: str,
        current_user: UserModel,
        query_type: str = "hybrid",
        top_k: int = 10,
        score_threshold: float | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute end-to-end Knowledge Engine search:
        Hybrid Search -> Re-ranking -> Record Search History Audit -> Return Results
        """
        start_time = time.time()

        # Fetch all candidate chunks for BM25 keyword matching
        all_chunks = []
        if query_type in ("keyword", "hybrid"):
            # Fetch chunks accessible to user
            is_admin = self.hybrid_search_service._is_user_admin(current_user)
            owner_filter = None if is_admin else current_user.id
            user_docs, _ = await self.doc_repo.list_documents(owner_id=owner_filter, limit=100)
            for doc in user_docs:
                chunks, _ = await self.chunk_repo.get_chunks_by_document_id(doc.id, limit=100)
                for chunk in chunks:
                    chunk.document = doc
                all_chunks.extend(chunks)

        # Execute Hybrid / Semantic / Keyword Search
        candidates = await self.hybrid_search_service.execute_search(
            query=query,
            current_user=current_user,
            query_type=query_type,
            top_k=top_k * 2,
            score_threshold=score_threshold,
            filters=filters,
            all_chunks=all_chunks,
        )

        # Re-rank candidates
        final_results = self.reranking_service.rerank_results(
            query=query,
            candidates=candidates,
            top_k=top_k,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Record Search History Audit
        try:
            await self.history_repo.create(
                user_id=current_user.id,
                query=query,
                query_type=query_type,
                result_count=len(final_results),
                latency_ms=latency_ms,
            )
        except Exception as exc:
            logger.error("Failed to record search history audit: %s", str(exc))

        return final_results

    async def search(
        self,
        query: str,
        user_id: uuid.UUID | str,
        search_mode: str = "hybrid",
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> SearchResponse:
        """
        Unified search endpoint for RAG ContextRetrievalService.
        """
        start_time = time.time()

        # Build dummy or real user model for access check
        u_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        current_user = UserModel(id=u_id, email="rag_user@blackrock.com", username="rag_user")

        results_dict = await self.search_knowledge_base(
            query=query,
            current_user=current_user,
            query_type=search_mode,
            top_k=top_k,
            filters=filters,
        )

        items: list[SearchResultItem] = []
        for r in results_dict:
            if isinstance(r, SearchResultItem):
                items.append(r)
            elif isinstance(r, dict):
                items.append(
                    SearchResultItem(
                        chunk_id=r.get("chunk_id", str(uuid.uuid4())),
                        document_id=r.get("document_id", str(uuid.uuid4())),
                        owner_id=r.get("owner_id"),
                        score=float(r.get("score", 1.0)),
                        page_number=int(r.get("page_number", 1)),
                        chunk_index=int(r.get("chunk_index", 0)),
                        snippet=r.get("text_snippet") or r.get("snippet") or r.get("text") or "",
                        highlighted_text=r.get("highlighted_text") or r.get("text_snippet") or "",
                        metadata=r.get("metadata") or {},
                    )
                )

        latency_ms = int((time.time() - start_time) * 1000)
        return SearchResponse(
            query=query,
            query_type=search_mode,
            total_results=len(items),
            latency_ms=latency_ms,
            results=items,
        )

    async def reindex_document(self, document_id: uuid.UUID | str) -> bool:
        """Purge old document vectors from Qdrant and re-compute embeddings."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        # Delete existing vectors
        await self.vector_service.delete_document_vectors(str(document_id))

        EventBus.publish(
            DocumentRemovedFromIndex(document_id=str(document_id))
        )

        # Re-process document
        return await self.process_document_embeddings(document_id)

    async def get_user_search_history(
        self,
        user_id: uuid.UUID | str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[SearchHistoryModel], int]:
        """Fetch search audit history records for a user."""
        return await self.history_repo.get_user_history(user_id=user_id, skip=skip, limit=limit)

    async def get_active_models(self) -> Sequence[EmbeddingModelModel]:
        """Fetch active embedding models registered in platform."""
        models = await self.model_repo.get_active_models()
        if not models:
            # Provide default registered model
            default_model = EmbeddingModelModel(
                id=uuid.uuid4(),
                name="sentence-transformers/all-MiniLM-L6-v2",
                dimension=384,
                provider="sentence-transformers",
                version="v1.0",
                is_active=True,
            )
            return [default_model]
        return models
