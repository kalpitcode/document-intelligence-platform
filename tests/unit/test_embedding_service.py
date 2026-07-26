"""
Unit Tests for Embedding Generation Service
"""

from __future__ import annotations

import pytest

from app.services.embedding_service import EmbeddingService, _generate_deterministic_vector


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_embedding_dimensions() -> None:
    service = EmbeddingService(model_name="sentence-transformers/all-MiniLM-L6-v2", dimension=384)
    vec = await service.generate_embedding("BlackRock Aladdin platform portfolio risk analysis")

    assert isinstance(vec, list)
    assert len(vec) == 384
    assert all(isinstance(v, float) for v in vec)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_embedding_empty_text() -> None:
    service = EmbeddingService(dimension=384)
    vec = await service.generate_embedding("   ")

    assert len(vec) == 384
    assert all(v == 0.0 for v in vec)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_batch_embeddings() -> None:
    service = EmbeddingService(dimension=384)
    texts = ["Asset allocation", "ESG compliance", "Liquidity risk management"]

    vectors = await service.generate_batch_embeddings(texts)

    assert len(vectors) == 3
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384


@pytest.mark.unit
def test_deterministic_vector_generator() -> None:
    vec1 = _generate_deterministic_vector("Financial markets", 384)
    vec2 = _generate_deterministic_vector("Financial markets", 384)
    vec3 = _generate_deterministic_vector("Derivatives trading", 384)

    assert vec1 == vec2
    assert vec1 != vec3
    assert len(vec1) == 384
