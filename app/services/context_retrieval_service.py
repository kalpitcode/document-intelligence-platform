"""
Context Retrieval Service Module
================================

Service responsible for preparing, deduplicating, score-filtering, and context-windowing
retrieved document chunks for RAG generation.

Architectural Rationale:
- Clean Architecture: Single Responsibility Principle (SRP) for chunk context window management.
- Token Budgeting: Uses `tiktoken` to strictly enforce prompt token budgets.
- Deduplication & Ordering: Preserves relative ranking order while stripping redundant text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence
import structlog
import tiktoken

from app.schemas.knowledge import SearchResultItem
from app.services.knowledge_orchestration_service import KnowledgeOrchestrationService

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RetrievedContextChunk:
    """Represents a clean, token-budgeted retrieved chunk ready for prompt insertion."""

    chunk_id: str
    document_id: str
    document_name: str
    page_number: int | None
    text: str
    score: float
    token_count: int


@dataclass(frozen=True)
class RetrievalContextEnvelope:
    """Container holding retrieved context chunks and token metrics."""

    chunks: list[RetrievedContextChunk]
    total_tokens: int
    raw_chunk_count: int
    deduplicated_chunk_count: int


class ContextRetrievalService:
    """Service handling chunk retrieval, deduplication, score filtering, and context windowing."""

    def __init__(
        self,
        knowledge_service: KnowledgeOrchestrationService,
        encoding_name: str = "cl100k_base",
    ) -> None:
        self.knowledge_service = knowledge_service
        try:
            self.tokenizer = tiktoken.get_encoding(encoding_name)
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count token length of a given text string using tiktoken."""
        if not text:
            return 0
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return len(text) // 4  # Fallback estimate

    async def get_retrieved_context(
        self,
        query: str,
        user_id: str,
        search_mode: str = "hybrid",
        top_k: int = 5,
        min_score: float = 0.1,
        max_context_tokens: int = 3000,
        filters: dict[str, Any] | None = None,
    ) -> RetrievalContextEnvelope:
        """
        Execute hybrid search, deduplicate results, filter by score, and limit to max_context_tokens.

        Args:
            query: User search query.
            user_id: Active user ID for security/visibility filtering.
            search_mode: "hybrid", "semantic", or "keyword".
            top_k: Number of raw candidate chunks to retrieve.
            min_score: Minimum relevance score threshold (default 0.1).
            max_context_tokens: Maximum token budget reserved for context chunks (default 3000).
            filters: Optional search payload metadata filters.

        Returns:
            RetrievalContextEnvelope containing clean chunks and context token budget stats.
        """
        # Step 1: Perform vector/hybrid search
        search_response = await self.knowledge_service.search(
            query=query,
            user_id=user_id,
            search_mode=search_mode,
            top_k=top_k,
            filters=filters,
        )

        raw_results: Sequence[SearchResultItem] = search_response.results
        raw_count = len(raw_results)

        # Step 2: Deduplicate chunks by chunk_id and exact text hashing
        seen_chunk_ids: set[str] = set()
        seen_text_hashes: set[int] = set()
        deduped_candidates: list[SearchResultItem] = []

        for item in raw_results:
            if item.score < min_score:
                continue

            chunk_id = item.chunk_id
            text_raw = getattr(item, "text", None) or item.snippet
            text_clean = text_raw.strip()
            text_hash = hash(text_clean)

            if chunk_id and chunk_id in seen_chunk_ids:
                continue
            if text_hash in seen_text_hashes:
                continue

            if chunk_id:
                seen_chunk_ids.add(chunk_id)
            seen_text_hashes.add(text_hash)
            deduped_candidates.append(item)

        dedup_count = len(deduped_candidates)

        # Step 3: Accumulate chunks within maximum context token budget
        final_chunks: list[RetrievedContextChunk] = []
        accumulated_tokens = 0

        for item in deduped_candidates:
            doc_name = getattr(item, "document_name", None) or item.metadata.get("filename") or "Enterprise Document"
            page_num = item.page_number
            text_raw = getattr(item, "text", None) or item.snippet
            chunk_text = text_raw.strip()
            chunk_tokens = self.count_tokens(chunk_text)

            # Check token budget
            if accumulated_tokens + chunk_tokens > max_context_tokens:
                # If adding this full chunk exceeds max_context_tokens, break to preserve ordering
                if not final_chunks:
                    # Truncate text if first chunk itself exceeds token limit
                    tokens = self.tokenizer.encode(chunk_text)[:max_context_tokens]
                    chunk_text = self.tokenizer.decode(tokens)
                    chunk_tokens = len(tokens)
                    final_chunks.append(
                        RetrievedContextChunk(
                            chunk_id=item.chunk_id,
                            document_id=item.document_id,
                            document_name=doc_name,
                            page_number=page_num,
                            text=chunk_text,
                            score=item.score,
                            token_count=chunk_tokens,
                        )
                    )
                    accumulated_tokens += chunk_tokens
                break

            final_chunks.append(
                RetrievedContextChunk(
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    document_name=doc_name,
                    page_number=page_num,
                    text=chunk_text,
                    score=item.score,
                    token_count=chunk_tokens,
                )
            )
            accumulated_tokens += chunk_tokens

        logger.info(
            "Retrieved RAG context window",
            raw_count=raw_count,
            dedup_count=dedup_count,
            final_count=len(final_chunks),
            total_context_tokens=accumulated_tokens,
        )

        return RetrievalContextEnvelope(
            chunks=final_chunks,
            total_tokens=accumulated_tokens,
            raw_chunk_count=raw_count,
            deduplicated_chunk_count=dedup_count,
        )
