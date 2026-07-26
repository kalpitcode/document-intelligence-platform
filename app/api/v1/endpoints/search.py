"""
Search & Knowledge Engine REST API Controller Module
====================================================

FastAPI controller handlers for semantic, keyword, and hybrid search execution,
user search history retrieval, document re-indexing, and embedding model registration endpoints.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Delegates to `KnowledgeOrchestrationService`.
- Enforces JWT authentication and RBAC permissions.
- Standard envelope response model `APIResponse[T]`.
- Detailed OpenAPI specs and error documentation.
"""

from __future__ import annotations

import time
from typing import Annotated, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cache_service import CacheService
from app.core.database.session import get_async_session
from app.core.exceptions.base import ForbiddenError, NotFoundError
from app.core.vector.qdrant_provider import QdrantProvider
from app.dependencies.auth import get_current_active_user
from app.models.user import UserModel
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_repository import (
    EmbeddingJobRepository,
    EmbeddingModelRepository,
    SearchHistoryRepository,
)
from app.repositories.processing_repository import DocumentChunkRepository
from app.schemas.base import APIResponse
from app.schemas.knowledge import (
    EmbeddingModelResponse,
    ReindexRequest,
    ReindexResponse,
    SearchHistoryItemResponse,
    SearchHistoryListResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search_service import HybridSearchService
from app.services.knowledge_orchestration_service import KnowledgeOrchestrationService
from app.services.reranking_service import RerankingService
from app.services.vector_service import VectorService
from app.workers.tasks.knowledge_tasks import reindex_documents_task

router = APIRouter(prefix="/search", tags=["Search & Knowledge Engine"])


async def get_knowledge_orchestration_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> KnowledgeOrchestrationService:
    """Dependency provider for KnowledgeOrchestrationService."""
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

    return KnowledgeOrchestrationService(
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


@router.post(
    "",
    response_model=APIResponse[SearchResponse],
    status_code=status.HTTP_200_OK,
    summary="Execute Hybrid / Semantic / Keyword Search",
    description="Transforms query string into searchable semantic knowledge using Qdrant dense vector search, Rank-BM25 keyword search, RRF score fusion, cross-encoder re-ranking, and metadata security filtering.",
)
async def search_endpoint(
    body: SearchRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    service: Annotated[KnowledgeOrchestrationService, Depends(get_knowledge_orchestration_service)],
) -> APIResponse[SearchResponse]:
    """Execute hybrid search over document chunk vector space."""
    start_time = time.time()
    try:
        filter_dict = body.filters.model_dump(exclude_none=True) if body.filters else None

        results = await service.search_knowledge_base(
            query=body.query,
            current_user=current_user,
            query_type=body.query_type.value,
            top_k=body.top_k,
            score_threshold=body.score_threshold,
            filters=filter_dict,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        response_items = [
            SearchResultItem(
                chunk_id=res["chunk_id"],
                document_id=res["document_id"],
                owner_id=res.get("owner_id"),
                score=res["score"],
                page_number=res.get("page_number", 1),
                chunk_index=res.get("chunk_index", 0),
                snippet=res["snippet"],
                highlighted_text=res["highlighted_text"],
                metadata=res.get("metadata", {}),
            )
            for res in results
        ]

        payload = SearchResponse(
            query=body.query,
            query_type=body.query_type.value,
            total_results=len(response_items),
            latency_ms=latency_ms,
            results=response_items,
        )

        await service.history_repo.session.commit()

        return APIResponse[SearchResponse](
            success=True,
            data=payload,
            message=f"Successfully executed {body.query_type.value} search. Found {len(response_items)} match(es).",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search execution failed: {type(exc).__name__} - {str(exc)}",
        ) from exc


@router.get(
    "/history",
    response_model=APIResponse[SearchHistoryListResponse],
    status_code=status.HTTP_200_OK,
    summary="Get User Search History Audit Records",
    description="Returns paginated search query execution history for the currently authenticated user.",
)
async def get_search_history_endpoint(
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    service: Annotated[KnowledgeOrchestrationService, Depends(get_knowledge_orchestration_service)],
    skip: Annotated[int, Query(ge=0, description="Records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Records limit")] = 50,
) -> APIResponse[SearchHistoryListResponse]:
    """Retrieve search history audit records."""
    records, total = await service.get_user_search_history(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    items = [
        SearchHistoryItemResponse(
            id=rec.id,
            query=rec.query,
            query_type=rec.query_type,
            result_count=rec.result_count,
            latency_ms=rec.latency_ms,
            created_at=rec.created_at,
        )
        for rec in records
    ]

    return APIResponse[SearchHistoryListResponse](
        success=True,
        data=SearchHistoryListResponse(items=items, total=total),
        message="Search history retrieved successfully",
    )


@router.post(
    "/reindex",
    response_model=APIResponse[ReindexResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Document Re-indexing",
    description="Purges existing vectors for a document from Qdrant and dispatches background Celery re-indexing task.",
)
async def reindex_document_endpoint(
    body: ReindexRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    service: Annotated[KnowledgeOrchestrationService, Depends(get_knowledge_orchestration_service)],
) -> APIResponse[ReindexResponse]:
    """Trigger background document re-indexing task."""
    try:
        doc_id = uuid.UUID(body.document_id)
        doc = await service.doc_repo.get_by_id(doc_id)
        if not doc:
            raise NotFoundError(f"Document with ID '{body.document_id}' not found")

        # Security check: document owner or admin
        is_admin = service.hybrid_search_service._is_user_admin(current_user)
        if not is_admin and str(doc.owner_id) != str(current_user.id):
            raise ForbiddenError("You do not have permission to re-index this document")

        # Dispatch Celery reindex task
        task_res = reindex_documents_task.delay(body.document_id)

        return APIResponse[ReindexResponse](
            success=True,
            data=ReindexResponse(
                document_id=body.document_id,
                message="Document re-indexing task dispatched to background Celery worker",
                job_id=task_res.id if hasattr(task_res, "id") else None,
            ),
            message="Re-indexing initiated successfully",
        )
    except (NotFoundError, ForbiddenError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindexing request failed: {type(exc).__name__} - {str(exc)}",
        ) from exc


@router.get(
    "/models",
    response_model=APIResponse[list[EmbeddingModelResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Active Embedding Models",
    description="Retrieves active embedding models registered in the platform for vector indexing.",
)
async def get_embedding_models_endpoint(
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    service: Annotated[KnowledgeOrchestrationService, Depends(get_knowledge_orchestration_service)],
) -> APIResponse[list[EmbeddingModelResponse]]:
    """Retrieve active embedding model specifications."""
    models = await service.get_active_models()

    items = [
        EmbeddingModelResponse(
            id=m.id,
            name=m.name,
            dimension=m.dimension,
            provider=m.provider,
            version=m.version,
            is_active=m.is_active,
        )
        for m in models
    ]

    return APIResponse[list[EmbeddingModelResponse]](
        success=True,
        data=items,
        message="Active embedding models retrieved successfully",
    )
