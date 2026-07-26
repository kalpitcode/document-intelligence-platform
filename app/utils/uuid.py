"""
UUID Utility Module
====================

Provides UUID generation helpers used across the application.

**Architectural Rationale:**
- Centralizes UUID generation so the format and version are consistent.
- UUID v4 (random) is the default for entity IDs.
- String representation helpers avoid repeated `str(uuid4())` calls.
- A deterministic UUID generator (v5) is available for testing/idempotency.
"""

from __future__ import annotations

import uuid


def generate_uuid() -> uuid.UUID:
    """Generate a random UUID v4."""
    return uuid.uuid4()


def generate_uuid_str() -> str:
    """Generate a random UUID v4 as a string."""
    return str(uuid.uuid4())


def generate_uuid_hex() -> str:
    """Generate a random UUID v4 as a hex string (no dashes)."""
    return uuid.uuid4().hex


def generate_deterministic_uuid(namespace: str, name: str) -> uuid.UUID:
    """
    Generate a deterministic UUID v5 based on a namespace and name.

    Useful for generating consistent UUIDs for the same input
    (e.g., idempotency keys, deduplication).

    Args:
        namespace: Namespace string.
        name: Name string.

    Returns:
        Deterministic UUID v5.
    """
    ns = uuid.uuid5(uuid.NAMESPACE_DNS, namespace)
    return uuid.uuid5(ns, name)


def is_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID.

    Args:
        value: String to validate.

    Returns:
        True if the string is a valid UUID.
    """
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError):
        return False
    return True
