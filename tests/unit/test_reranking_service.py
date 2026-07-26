"""
Unit Tests for Re-ranking & Snippet Highlighting Service
"""

from __future__ import annotations

import pytest

from app.services.reranking_service import RerankingService


@pytest.mark.unit
def test_highlight_terms() -> None:
    service = RerankingService()
    text = "The quarterly portfolio performance revenue grew by 15%."
    query_terms = ["portfolio", "revenue"]

    highlighted = service.highlight_terms(text, query_terms)

    assert "<mark>portfolio</mark>" in highlighted
    assert "<mark>revenue</mark>" in highlighted


@pytest.mark.unit
def test_rerank_results_sorting() -> None:
    service = RerankingService()
    candidates = [
        {
            "id": "c1",
            "score": 0.5,
            "payload": {"chunk_id": "c1", "document_id": "d1", "text_snippet": "Unrelated financial text"},
        },
        {
            "id": "c2",
            "score": 0.6,
            "payload": {
                "chunk_id": "c2",
                "document_id": "d2",
                "text_snippet": "Exact portfolio risk management analysis revenue report",
            },
        },
    ]

    reranked = service.rerank_results(query="portfolio risk management", candidates=candidates, top_k=5)

    assert len(reranked) == 2
    assert reranked[0]["chunk_id"] == "c2"
    assert "<mark>portfolio</mark>" in reranked[0]["highlighted_text"]
