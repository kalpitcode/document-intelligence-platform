"""
Unit Tests for RAG Citation Generation
=======================================

Tests for citation extraction and retrieved document summary formatting in RAGService.
"""

from unittest.mock import MagicMock
from app.services.context_retrieval_service import RetrievedContextChunk
from app.services.rag_service import RAGService


def test_rag_citation_extraction():
    """Verify RAGService produces exact Document Name, Page Number, and Chunk ID citations."""
    service = RAGService(
        context_retrieval_service=MagicMock(),
        prompt_builder_service=MagicMock(),
        llm_service=MagicMock(),
        session_repo=MagicMock(),
        message_repo=MagicMock(),
        usage_log_repo=MagicMock(),
    )

    chunks = [
        RetrievedContextChunk(
            chunk_id="chunk-abc",
            document_id="doc-xyz",
            document_name="Annual_Report_2025.pdf",
            page_number=12,
            text="Global assets under management reached $10 Trillion.",
            score=0.98,
            token_count=15,
        ),
        RetrievedContextChunk(
            chunk_id="chunk-def",
            document_id="doc-xyz",
            document_name="Annual_Report_2025.pdf",
            page_number=14,
            text="Technology investments expanded by 20%.",
            score=0.89,
            token_count=12,
        ),
    ]

    citations = service._extract_citations(chunks)
    assert len(citations) == 2
    assert citations[0].document_name == "Annual_Report_2025.pdf"
    assert citations[0].page_number == 12
    assert citations[0].chunk_id == "chunk-abc"
    assert "assets under management" in citations[0].snippet

    retrieved_docs = service._extract_retrieved_documents(chunks)
    assert len(retrieved_docs) == 1
    assert retrieved_docs[0].document_id == "doc-xyz"
    assert retrieved_docs[0].title == "Annual_Report_2025.pdf"
