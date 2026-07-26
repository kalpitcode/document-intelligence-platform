"""
Storage Provider Abstract Base Module
======================================

Defines the abstract interface for object storage operations.

**Architectural Rationale:**
- Provider Independence: Allows switching between MinIO, AWS S3, Azure Blob, and GCP
  without modifying any service or business logic.
- Follows the Strategy Pattern and Dependency Inversion Principle (DIP).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """Abstract Base Class defining object storage provider capabilities."""

    @abstractmethod
    async def upload(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload raw bytes to object storage.

        Args:
            file_data: Binary file content.
            object_name: Target object key/path in bucket.
            content_type: MIME type of the file.

        Returns:
            Storage path / URI of the uploaded object.
        """

    @abstractmethod
    async def download(self, object_name: str) -> bytes:
        """
        Download binary object from storage.

        Args:
            object_name: Object key/path to retrieve.

        Returns:
            Raw bytes of the requested object.
        """

    @abstractmethod
    async def delete(self, object_name: str) -> bool:
        """
        Delete object from storage.

        Args:
            object_name: Object key/path to delete.

        Returns:
            True if deleted successfully, False otherwise.
        """

    @abstractmethod
    async def copy(self, source_object: str, dest_object: str) -> bool:
        """
        Copy object from source path to destination path.

        Args:
            source_object: Source object key.
            dest_object: Destination object key.

        Returns:
            True if copied successfully.
        """

    @abstractmethod
    async def move(self, source_object: str, dest_object: str) -> bool:
        """
        Move object from source to destination.

        Args:
            source_object: Source object key.
            dest_object: Destination object key.

        Returns:
            True if moved successfully.
        """

    @abstractmethod
    async def exists(self, object_name: str) -> bool:
        """
        Check if object exists in storage.

        Args:
            object_name: Object key to verify.

        Returns:
            True if exists, False otherwise.
        """

    @abstractmethod
    async def generate_presigned_url(
        self,
        object_name: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate presigned download URL for an object.

        Args:
            object_name: Object key.
            expires_in: URL validity duration in seconds.

        Returns:
            Presigned HTTP GET URL string.
        """

    @abstractmethod
    async def list_files(self, prefix: str = "") -> list[str]:
        """
        List stored object keys matching prefix.

        Args:
            prefix: Key prefix filter.

        Returns:
            List of matching object keys.
        """
