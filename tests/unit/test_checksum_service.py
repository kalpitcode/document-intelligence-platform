"""
Unit Tests for Checksum Service
=================================
"""

from __future__ import annotations

import io

from app.services.checksum_service import ChecksumService


def test_sha256_bytes_calculation() -> None:
    content = b"BlackRock Aladdin Document Intelligence Platform"
    hash_str = ChecksumService.calculate_sha256_bytes(content)

    assert len(hash_str) == 64
    assert isinstance(hash_str, str)
    # Check consistency
    assert hash_str == ChecksumService.calculate_sha256_bytes(content)


def test_sha256_stream_calculation() -> None:
    content = b"BlackRock Stream Test Content" * 100
    stream = io.BytesIO(content)

    hash_from_stream = ChecksumService.calculate_sha256_stream(stream)
    hash_from_bytes = ChecksumService.calculate_sha256_bytes(content)

    assert hash_from_stream == hash_from_bytes
    # Stream position should be reset to 0
    assert stream.tell() == 0
