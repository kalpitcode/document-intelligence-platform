"""
Unit Tests for Chunking Service Module
"""

from __future__ import annotations

import uuid
import pytest

from app.services.chunking_service import ChunkingService


@pytest.mark.unit
def test_create_chunks_deterministic_sliding_window() -> None:
    service = ChunkingService(target_chunk_words=10, overlap_words=2)
    doc_id = uuid.uuid4()
    words = [f"word{i}" for i in range(25)]
    text = " ".join(words)

    chunks = service.create_chunks(doc_id, text)

    assert len(chunks) > 1
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert chunks[0].document_id == doc_id
    assert chunks[0].start_offset == 0
    assert chunks[0].token_estimate > 0


@pytest.mark.unit
def test_create_chunks_empty_text() -> None:
    service = ChunkingService()
    doc_id = uuid.uuid4()
    assert service.create_chunks(doc_id, "") == []
