"""
Hashing Utility Module
========================

Provides generic hashing utilities for checksums and data integrity.

**Architectural Rationale:**
- Centralizes hashing so algorithm choices are consistent.
- SHA-256 is the default for security-sensitive operations.
- MD5 is available for non-security checksums (e.g., file deduplication).
- Password hashing is NOT in this module — it belongs in an auth
  service (future) using bcrypt/argon2.
"""

from __future__ import annotations

import hashlib


def sha256_hash(data: str | bytes) -> str:
    """
    Generate a SHA-256 hash.

    Args:
        data: String or bytes to hash.

    Returns:
        Hexadecimal hash string.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def md5_hash(data: str | bytes) -> str:
    """
    Generate an MD5 hash.

    WARNING: MD5 is NOT cryptographically secure. Use only for
    checksums and deduplication, never for security.

    Args:
        data: String or bytes to hash.

    Returns:
        Hexadecimal hash string.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.md5(data).hexdigest()  # noqa: S324


def file_checksum(filepath: str, algorithm: str = "sha256") -> str:
    """
    Calculate a file checksum.

    Reads the file in chunks to handle large files efficiently.

    Args:
        filepath: Path to the file.
        algorithm: Hash algorithm ('sha256' or 'md5').

    Returns:
        Hexadecimal checksum string.
    """
    hash_func = hashlib.new(algorithm)
    chunk_size = 8192

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hash_func.update(chunk)

    return hash_func.hexdigest()
