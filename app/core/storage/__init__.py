"""
Storage Package
===============

Provides object storage abstraction and providers.
"""

from __future__ import annotations

from app.core.storage.base import StorageProvider
from app.core.storage.minio_provider import MinIOStorageProvider

__all__ = ["MinIOStorageProvider", "StorageProvider"]
