"""
Checksum Service Module
========================

Provides stream-capable SHA256 hash generation for duplicate detection and file integrity.
"""

from __future__ import annotations

import hashlib
import io
from typing import BinaryIO


class ChecksumService:
    """Service for computing SHA256 file checksums efficiently."""

    CHUNK_SIZE: int = 64 * 1024  # 64 KB chunks

    @classmethod
    def calculate_sha256_bytes(cls, content: bytes) -> str:
        """
        Compute SHA256 hex digest for a byte string.

        Args:
            content: Raw byte string.

        Returns:
            64-character lowercase hexadecimal SHA256 string.
        """
        return hashlib.sha256(content).hexdigest()

    @classmethod
    def calculate_sha256_stream(cls, stream: BinaryIO) -> str:
        """
        Compute SHA256 hex digest from a binary stream in chunks.

        Args:
            stream: Readable binary stream.

        Returns:
            64-character lowercase hexadecimal SHA256 string.
        """
        hasher = hashlib.sha256()
        stream.seek(0)
        while chunk := stream.read(cls.CHUNK_SIZE):
            hasher.update(chunk)
        stream.seek(0)
        return hasher.hexdigest()
