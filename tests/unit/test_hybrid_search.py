"""
Unit Tests for Hybrid Search & Reciprocal Rank Fusion
"""

from __future__ import annotations

from unittest.mock import MagicMock
import uuid

import pytest

from app.models.user import UserModel
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_search_service import HybridSearchService
from app.services.vector_service import VectorService


@pytest.mark.unit
def test_reciprocal_rank_fusion() -> None:
    embedding_service = MagicMock(spec=EmbeddingService)
    vector_service = MagicMock(spec=VectorService)
    service = HybridSearchService(vector_service, embedding_service)

    semantic = [
        {"id": "c1", "score": 0.9, "payload": {"text_snippet": "Doc 1 text"}},
        {"id": "c2", "score": 0.8, "payload": {"text_snippet": "Doc 2 text"}},
    ]
    keyword = [
        {"id": "c2", "score": 0.95, "payload": {"text_snippet": "Doc 2 text"}},
        {"id": "c3", "score": 0.7, "payload": {"text_snippet": "Doc 3 text"}},
    ]

    fused = service._reciprocal_rank_fusion(semantic, keyword, rrf_k=60)

    assert len(fused) == 3
    # c2 appears in both lists, so it should have the highest RRF fused score
    assert fused[0]["id"] == "c2"
    assert 0.0 <= fused[0]["score"] <= 1.0


@pytest.mark.unit
def test_build_security_filters_non_admin() -> None:
    embedding_service = MagicMock(spec=EmbeddingService)
    vector_service = MagicMock(spec=VectorService)
    service = HybridSearchService(vector_service, embedding_service)

    user = MagicMock(spec=UserModel)
    user.id = uuid.uuid4()
    user.roles = []

    filters = service._build_security_filters(user, {"mime_type": "application/pdf"})

    assert filters["owner_id"] == str(user.id)
    assert filters["mime_type"] == "application/pdf"
