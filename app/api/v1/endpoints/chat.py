"""
RAG Chat Engine REST API Controller Module
===========================================

FastAPI controller endpoints for multi-turn grounded RAG Chat execution,
session management, and message history.

Endpoints:
- POST /api/v1/chat: Submit a question to initiate/continue a grounded RAG session.
- POST /api/v1/chat/{session_id}: Submit a question to a specific active chat session.
- GET /api/v1/chat/sessions: List paginated user chat session threads.
- GET /api/v1/chat/{session_id}: Get chat session metadata and message history.
- DELETE /api/v1/chat/{session_id}: Delete a chat session and its conversation messages.

Architectural Rationale:
- Enforces JWT authentication (`get_current_active_user`).
- Standard envelope response model `APIResponse[T]`.
- Enforces strict OpenAPI specifications and error documentation.
"""

from __future__ import annotations

from typing import Annotated, Any
import uuid
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_async_session
from app.core.exceptions.base import NotFoundError
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
from app.repositories.rag_repository import ChatMessageRepository, ChatSessionRepository, LLMUsageLogRepository
from app.schemas.base import APIResponse
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
from app.services.context_retrieval_service import ContextRetrievalService
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search_service import HybridSearchService
from app.services.knowledge_orchestration_service import KnowledgeOrchestrationService
from app.services.llm_service import LLMService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.rag_service import RAGService
from app.services.reranking_service import RerankingService
from app.services.vector_service import VectorService

router = APIRouter(prefix="/chat", tags=["RAG Chat Engine"])


async def get_rag_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> RAGService:
    """Dependency provider instantiating RAGService with full dependency graph."""
    doc_repo = DocumentRepository(session)
    chunk_repo = DocumentChunkRepository(session)
    job_repo = EmbeddingJobRepository(session)
    history_repo = SearchHistoryRepository(session)
    model_repo = EmbeddingModelRepository(session)

    qdrant_provider = QdrantProvider()
    vector_service = VectorService(vector_provider=qdrant_provider)
    embedding_service = EmbeddingService()
    hybrid_search_service = HybridSearchService(
        vector_service=vector_service,
        embedding_service=embedding_service,
    )
    reranking_service = RerankingService()

    knowledge_service = KnowledgeOrchestrationService(
        embedding_job_repo=job_repo,
        search_history_repo=history_repo,
        embedding_model_repo=model_repo,
        chunk_repo=chunk_repo,
        doc_repo=doc_repo,
        embedding_service=embedding_service,
        vector_service=vector_service,
        hybrid_search_service=hybrid_search_service,
        reranking_service=reranking_service,
    )

    context_retrieval_service = ContextRetrievalService(knowledge_service=knowledge_service)
    prompt_builder_service = PromptBuilderService()
    llm_service = LLMService()

    session_repo = ChatSessionRepository(session)
    message_repo = ChatMessageRepository(session)
    usage_log_repo = LLMUsageLogRepository(session)

    return RAGService(
        context_retrieval_service=context_retrieval_service,
        prompt_builder_service=prompt_builder_service,
        llm_service=llm_service,
        session_repo=session_repo,
        message_repo=message_repo,
        usage_log_repo=usage_log_repo,
    )


@router.post(
    "",
    response_model=APIResponse[RAGChatResponse],
    status_code=status.HTTP_200_OK,
    summary="Submit a RAG Chat Question",
    description="Submit a question to execute grounded RAG search & LLM generation. Answers are guaranteed zero-hallucination, derived exclusively from indexed enterprise documents with mandatory citations.",
)
async def create_chat_message(
    request: RAGChatRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
) -> APIResponse[RAGChatResponse]:
    """Execute end-to-end RAG question answering pipeline."""
    result = await rag_service.execute_rag_pipeline(
        user_id=current_user.id,
        question=request.question,
        session_id=request.session_id,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        search_mode=request.search_mode,
        top_k=request.top_k,
        filters=request.filters,
    )

    citations_api = [
        CitationItem(
            document_id=c.document_id,
            document_name=c.document_name,
            page_number=c.page_number,
            chunk_id=c.chunk_id,
            snippet=c.snippet,
            score=c.score,
        )
        for c in result.citations
    ]

    retrieved_docs_api = [
        RetrievedDocumentItem(
            document_id=d.document_id,
            title=d.title,
            page_number=d.page_number,
            score=d.score,
        )
        for d in result.retrieved_documents
    ]

    response_data = RAGChatResponse(
        session_id=result.session_id,
        message_id=result.message_id,
        answer=result.answer,
        citations=citations_api,
        retrieved_documents=retrieved_docs_api,
        latency=LatencyMetrics(
            prompt_build_time_ms=result.prompt_build_time_ms,
            retrieval_time_ms=result.retrieval_time_ms,
            generation_time_ms=result.generation_time_ms,
            total_latency_ms=result.total_latency_ms,
        ),
        token_usage=TokenUsage(
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            cost=result.cost,
        ),
        model=result.model,
    )

    return APIResponse(
        data=response_data,
        message="RAG answer generated successfully.",
    )


@router.post(
    "/{session_id}",
    response_model=APIResponse[RAGChatResponse],
    status_code=status.HTTP_200_OK,
    summary="Continue Chat Session",
    description="Submit a follow-up question to an existing active chat session.",
)
async def continue_chat_session(
    session_id: Annotated[uuid.UUID, Path(..., description="Target chat session UUID.")],
    request: RAGChatRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
) -> APIResponse[RAGChatResponse]:
    """Continue existing RAG chat session thread."""
    request.session_id = session_id
    return await create_chat_message(
        request=request,
        current_user=current_user,
        rag_service=rag_service,
    )


@router.get(
    "/sessions",
    response_model=APIResponse[ChatSessionListResponse],
    status_code=status.HTTP_200_OK,
    summary="Get User Chat Sessions",
    description="Retrieve paginated list of chat sessions created by the current authenticated user.",
)
async def get_user_chat_sessions(
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
    page: Annotated[int, Query(ge=1, description="Page number (1-based).")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Items per page.")] = 20,
) -> APIResponse[ChatSessionListResponse]:
    """List paginated RAG chat session threads."""
    skip = (page - 1) * size
    sessions, total = await rag_service.get_user_sessions(
        user_id=current_user.id,
        skip=skip,
        limit=size,
    )

    items = [
        ChatSessionResponse(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
            last_message_at=s.last_message_at,
        )
        for s in sessions
    ]

    return APIResponse(
        data=ChatSessionListResponse(
            items=items,
            total=total,
            page=page,
            size=size,
        ),
        message="Retrieved chat sessions successfully.",
    )


@router.get(
    "/{session_id}",
    response_model=APIResponse[ChatSessionDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Chat Session Detail & History",
    description="Retrieve chat session metadata and full chronological conversation message history.",
)
async def get_chat_session_detail(
    session_id: Annotated[uuid.UUID, Path(..., description="Target chat session UUID.")],
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
) -> APIResponse[ChatSessionDetailResponse]:
    """Retrieve chat session details and message history."""
    session, messages = await rag_service.get_session_history(
        session_id=session_id,
        user_id=current_user.id,
    )

    session_resp = ChatSessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        last_message_at=session.last_message_at,
    )

    messages_resp = [
        ChatMessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            message=m.message,
            citations=m.citations or [],
            token_count=m.token_count,
            latency_ms=m.latency_ms,
            created_at=m.created_at,
        )
        for m in messages
    ]

    return APIResponse(
        data=ChatSessionDetailResponse(
            session=session_resp,
            messages=messages_resp,
        ),
        message="Retrieved chat session history successfully.",
    )


@router.delete(
    "/{session_id}",
    response_model=APIResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Delete Chat Session",
    description="Delete a chat session and all associated conversation history messages.",
)
async def delete_chat_session(
    session_id: Annotated[uuid.UUID, Path(..., description="Target chat session UUID.")],
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    rag_service: Annotated[RAGService, Depends(get_rag_service)],
) -> APIResponse[dict[str, Any]]:
    """Delete RAG chat session."""
    deleted = await rag_service.delete_session(
        session_id=session_id,
        user_id=current_user.id,
    )
    if not deleted:
        raise NotFoundError(f"ChatSession {session_id} not found or permission denied.")

    return APIResponse(
        data={"session_id": str(session_id), "deleted": True},
        message="Chat session deleted successfully.",
    )
