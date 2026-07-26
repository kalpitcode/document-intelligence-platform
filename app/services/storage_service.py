"""
Storage Service Module
======================

Orchestrates storage operations via the injected StorageProvider strategy.
"""

from __future__ import annotations

from app.core.storage.base import StorageProvider


class StorageService:
    """Service encapsulating storage strategy interactions."""

    def __init__(self, provider: StorageProvider) -> None:
        self.provider = provider

    async def store_file(
        self,
        file_bytes: bytes,
        object_key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Store raw binary content into object storage."""
        return await self.provider.upload(file_bytes, object_key, content_type)

    async def get_file_content(self, object_key: str) -> bytes:
        """Retrieve raw binary object from storage."""
        return await self.provider.download(object_key)

    async def delete_file(self, object_key: str) -> bool:
        """Remove file object from storage."""
        return await self.provider.delete(object_key)

    async def get_presigned_download_url(
        self,
        object_key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate secure presigned download link."""
        return await self.provider.generate_presigned_url(object_key, expires_in)

    async def file_exists(self, object_key: str) -> bool:
        """Check if file object exists."""
        return await self.provider.exists(object_key)
