"""
Unit Tests for Prompt Builder Service
=====================================

Tests for PromptBuilderService system prompt directives, context block formatting, and token counting.
"""

from app.services.context_retrieval_service import RetrievedContextChunk
from app.services.prompt_builder_service import PromptBuilderService


def test_prompt_builder_formatting_and_directives():
    """Verify PromptBuilderService constructs zero-hallucination prompt envelope."""
    builder = PromptBuilderService()

    chunks = [
        RetrievedContextChunk(
            chunk_id="chk-100",
            document_id="doc-100",
            document_name="Q4_Financials.pdf",
            page_number=3,
            text="Net income increased by 15% year-over-year.",
            score=0.92,
            token_count=10,
        )
    ]

    question = "What was the net income increase?"
    envelope = builder.build_prompt(user_question=question, chunks=chunks)

    assert "STRICT RULES & CONSTRAINTS:" in envelope.system_prompt
    assert "Never fabricate or hallucinate" in envelope.system_prompt
    assert "Q4_Financials.pdf" in envelope.user_prompt
    assert "Page 3" in envelope.user_prompt
    assert "chk-100" in envelope.user_prompt
    assert question in envelope.user_prompt
    assert envelope.prompt_tokens > 0


def test_prompt_builder_empty_context():
    """Verify PromptBuilderService handles empty context gracefully."""
    builder = PromptBuilderService()
    envelope = builder.build_prompt(user_question="Random question", chunks=[])

    assert "No relevant enterprise document context found." in envelope.user_prompt
    assert "Random question" in envelope.user_prompt
