"""
RAG Service Master Orchestration Module
=======================================

Master orchestration service for Enterprise Retrieval-Augmented Generation (RAG).

Architectural Rationale:
- Clean Architecture & Service Layer: Unites ContextRetrievalService, PromptBuilderService,
  LLMService, and RAG Repositories into a cohesive pipeline.
- Security RBAC: Enforces RBAC document visibility security prior to vector retrieval.
- Observability: Measures Prompt Build Time, Retrieval Time, Generation Time, Total Latency,
  Token Usage, and Cost metrics.
- Grounded Citations: Extracts exact Document Name, Page Number, and Chunk Reference for every statement.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Sequence
import uuid
import structlog

from app.models.rag import ChatMessageModel, ChatSessionModel
from app.repositories.rag_repository import ChatMessageRepository, ChatSessionRepository, LLMUsageLogRepository
from app.services.context_retrieval_service import ContextRetrievalService, RetrievalContextEnvelope, RetrievedContextChunk
from app.services.llm_service import LLMService
from app.services.prompt_builder_service import PromptBuilderService

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Citation:
    """Structured citation item for grounded claims."""

    document_id: str
    document_name: str
    page_number: int | None
    chunk_id: str
    snippet: str
    score: float


@dataclass(frozen=True)
class RetrievedDocumentSummary:
    """Summary of document retrieved during search."""

    document_id: str
    title: str
    page_number: int | None
    score: float


@dataclass(frozen=True)
class RAGPipelineResult:
    """Final outcome envelope returned by RAGService."""

    session_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    citations: list[Citation]
    retrieved_documents: list[RetrievedDocumentSummary]
    prompt_build_time_ms: int
    retrieval_time_ms: int
    generation_time_ms: int
    total_latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    model: str


class RAGService:
    """Master Orchestrator service driving the enterprise RAG Chat Engine."""

    def __init__(
        self,
        context_retrieval_service: ContextRetrievalService,
        prompt_builder_service: PromptBuilderService,
        llm_service: LLMService,
        session_repo: ChatSessionRepository,
        message_repo: ChatMessageRepository,
        usage_log_repo: LLMUsageLogRepository,
    ) -> None:
        self.context_retrieval_service = context_retrieval_service
        self.prompt_builder_service = prompt_builder_service
        self.llm_service = llm_service
        self.session_repo = session_repo
        self.message_repo = message_repo
        self.usage_log_repo = usage_log_repo

    async def execute_rag_pipeline(
        self,
        user_id: uuid.UUID | str,
        question: str,
        session_id: uuid.UUID | str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        search_mode: str = "hybrid",
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> RAGPipelineResult:
        """
        Execute end-to-end RAG Chat pipeline.

        1. Session initialization / validation.
        2. Context Retrieval (hybrid search + deduplication + RBAC filtering + context windowing).
        3. Grounded Prompt Assembly.
        4. LLM Generation.
        5. Citation extraction.
        6. Usage audit logging & conversation history persistence.
        """
        total_start_time = time.perf_counter()
        u_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

        # 1. Manage Chat Session
        session: ChatSessionModel | None = None
        if session_id:
            s_id = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
            session = await self.session_repo.get_session_by_id_and_user(s_id, u_id)

        if not session:
            session_title = question[:50] + "..." if len(question) > 50 else question
            session = await self.session_repo.create(
                user_id=u_id,
                title=session_title,
            )

        # Persist user question message
        await self.message_repo.create(
            session_id=session.id,
            role="user",
            message=question,
            citations=[],
            token_count=self.prompt_builder_service.count_tokens(question),
            latency_ms=0,
        )

        # 2. Retrieval Phase
        retrieval_start = time.perf_counter()
        context_envelope: RetrievalContextEnvelope = await self.context_retrieval_service.get_retrieved_context(
            query=question,
            user_id=str(u_id),
            search_mode=search_mode,
            top_k=top_k,
            max_context_tokens=3000,
            filters=filters,
        )
        retrieval_time_ms = int((time.perf_counter() - retrieval_start) * 1000)

        # 3. Prompt Building Phase
        prompt_start = time.perf_counter()
        prompt_envelope = self.prompt_builder_service.build_prompt(
            user_question=question,
            chunks=context_envelope.chunks,
        )
        prompt_build_time_ms = int((time.perf_counter() - prompt_start) * 1000)

        # 4. LLM Generation Phase
        gen_start = time.perf_counter()
        llm_response = await self.llm_service.generate(
            prompt=prompt_envelope.user_prompt,
            system_prompt=prompt_envelope.system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        generation_time_ms = int((time.perf_counter() - gen_start) * 1000)

        # 5. Extract Citations & Retrieved Documents Summary
        citations: list[Citation] = self._extract_citations(context_envelope.chunks)
        retrieved_docs: list[RetrievedDocumentSummary] = self._extract_retrieved_documents(context_envelope.chunks)

        total_latency_ms = int((time.perf_counter() - total_start_time) * 1000)

        # Convert citations for JSON DB storage
        citations_json = [
            {
                "document_id": c.document_id,
                "document_name": c.document_name,
                "page_number": c.page_number,
                "chunk_id": c.chunk_id,
                "snippet": c.snippet,
                "score": c.score,
            }
            for c in citations
        ]

        # 6. Persist Assistant Response Message
        assistant_msg = await self.message_repo.create(
            session_id=session.id,
            role="assistant",
            message=llm_response.content,
            citations=citations_json,
            token_count=llm_response.completion_tokens,
            latency_ms=generation_time_ms,
        )

        # Touch session last_message_at timestamp
        await self.session_repo.touch_session(session)

        # 7. Audit Log Usage with Telemetry & Metadata
        retrieved_chunk_ids = [c.chunk_id for c in context_envelope.chunks]
        retrieval_scores = [c.score for c in context_envelope.chunks]
        await self.usage_log_repo.log_usage(
            user_id=u_id,
            model=llm_response.model_name,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
            cost=llm_response.estimated_cost,
            latency_ms=total_latency_ms,
            prompt_template_name=prompt_envelope.template_name,
            prompt_version=prompt_envelope.template_version,
            retrieved_chunk_ids=retrieved_chunk_ids,
            retrieval_scores=retrieval_scores,
            retrieval_strategy=search_mode,
        )

        # Commit session transaction
        await self.session_repo.session.commit()

        logger.info(
            "RAG pipeline completed successfully",
            session_id=str(session.id),
            message_id=str(assistant_msg.id),
            citations_count=len(citations),
            total_latency_ms=total_latency_ms,
        )

        return RAGPipelineResult(
            session_id=session.id,
            message_id=assistant_msg.id,
            answer=llm_response.content,
            citations=citations,
            retrieved_documents=retrieved_docs,
            prompt_build_time_ms=prompt_build_time_ms,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
            total_latency_ms=total_latency_ms,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
            cost=llm_response.estimated_cost,
            model=llm_response.model_name,
        )

    def _extract_citations(self, chunks: list[RetrievedContextChunk]) -> list[Citation]:
        """Convert retrieved context chunks into grounded citation items."""
        citations = []
        for chunk in chunks:
            snippet = chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text
            citations.append(
                Citation(
                    document_id=chunk.document_id,
                    document_name=chunk.document_name,
                    page_number=chunk.page_number,
                    chunk_id=chunk.chunk_id,
                    snippet=snippet,
                    score=chunk.score,
                )
            )
        return citations

    def _extract_retrieved_documents(
        self, chunks: list[RetrievedContextChunk]
    ) -> list[RetrievedDocumentSummary]:
        """Extract unique document summaries from retrieved chunks."""
        seen_docs: set[str] = set()
        docs = []
        for chunk in chunks:
            if chunk.document_id not in seen_docs:
                seen_docs.add(chunk.document_id)
                docs.append(
                    RetrievedDocumentSummary(
                        document_id=chunk.document_id,
                        title=chunk.document_name,
                        page_number=chunk.page_number,
                        score=chunk.score,
                    )
                )
        return docs

    async def get_user_sessions(
        self, user_id: uuid.UUID | str, skip: int = 0, limit: int = 50
    ) -> tuple[Sequence[ChatSessionModel], int]:
        """Get paginated chat sessions for a user."""
        return await self.session_repo.get_user_sessions(user_id, skip=skip, limit=limit)

    async def get_session_history(
        self, session_id: uuid.UUID | str, user_id: uuid.UUID | str
    ) -> tuple[ChatSessionModel, Sequence[ChatMessageModel]]:
        """Get a session and its message history with ownership verification."""
        session = await self.session_repo.get_session_by_id_and_user(session_id, user_id)
        if not session:
            from app.core.exceptions.base import NotFoundError
            raise NotFoundError(f"ChatSession {session_id} not found for current user")

        messages = await self.message_repo.get_session_messages(session.id)
        return session, messages

    async def delete_session(self, session_id: uuid.UUID | str, user_id: uuid.UUID | str) -> bool:
        """Delete a chat session and cascade delete its messages."""
        session = await self.session_repo.get_session_by_id_and_user(session_id, user_id)
        if not session:
            return False
        await self.session_repo.delete(session)
        await self.session_repo.session.commit()
        return True
