"""
Unit Tests for Context Retrieval Service
========================================

Tests for ContextRetrievalService deduplication, score filtering, and token windowing.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
from app.schemas.knowledge import SearchResponse, SearchResultItem
from app.services.context_retrieval_service import ContextRetrievalService


@pytest.fixture
def mock_knowledge_service():
    service = MagicMock()
    service.search = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_context_retrieval_deduplication_and_windowing(mock_knowledge_service):
    """Test that ContextRetrievalService deduplicates chunks and obeys max context token budget."""
    mock_items = [
        SearchResultItem(
            chunk_id="chunk-1",
            document_id="doc-1",
            score=0.95,
            page_number=1,
            snippet="First unique chunk text explaining financial growth.",
            highlighted_text="First unique chunk text explaining <em>financial growth</em>.",
            metadata={"filename": "doc_1.pdf"},
        ),
        SearchResultItem(
            chunk_id="chunk-1",  # Duplicate chunk_id
            document_id="doc-1",
            score=0.95,
            page_number=1,
            snippet="First unique chunk text explaining financial growth.",
            highlighted_text="First unique chunk text explaining <em>financial growth</em>.",
            metadata={"filename": "doc_1.pdf"},
        ),
        SearchResultItem(
            chunk_id="chunk-2",
            document_id="doc-1",
            score=0.85,
            page_number=2,
            snippet="Second unique chunk describing asset management strategy.",
            highlighted_text="Second unique chunk describing asset management strategy.",
            metadata={"filename": "doc_1.pdf"},
        ),
        SearchResultItem(
            chunk_id="chunk-3",
            document_id="doc-2",
            score=0.05,  # Below min_score (0.10)
            page_number=5,
            snippet="Low score candidate below threshold.",
            highlighted_text="Low score candidate below threshold.",
            metadata={"filename": "doc_2.pdf"},
        ),
    ]

    mock_knowledge_service.search.return_value = SearchResponse(
        query="growth strategy",
        query_type="hybrid",
        total_results=len(mock_items),
        latency_ms=10,
        results=mock_items,
    )

    retrieval_service = ContextRetrievalService(knowledge_service=mock_knowledge_service)
    envelope = await retrieval_service.get_retrieved_context(
        query="growth strategy",
        user_id="user-123",
        search_mode="hybrid",
        top_k=5,
        min_score=0.10,
        max_context_tokens=1000,
    )

    assert envelope.raw_chunk_count == 4
    assert envelope.deduplicated_chunk_count == 2
    assert len(envelope.chunks) == 2
    assert envelope.chunks[0].chunk_id == "chunk-1"
    assert envelope.chunks[1].chunk_id == "chunk-2"
    assert envelope.total_tokens > 0
