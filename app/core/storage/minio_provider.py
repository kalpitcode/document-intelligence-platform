"""
MinIO Object Storage Provider Module
=====================================

Implements the StorageProvider interface for MinIO / S3 compatible object stores.

**Architectural Rationale:**
- Provides high-performance object storage operations.
- Automatically creates bucket on startup if missing.
- Includes in-memory mock fallback when MinIO instance is unreachable or library is absent.
"""

from __future__ import annotations

from datetime import timedelta
import io
import logging
from typing import Any

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    Minio = None  # type: ignore[assignment, misc]
    S3Error = Exception  # type: ignore[assignment, misc]
    MINIO_AVAILABLE = False

from app.core.config import get_settings
from app.core.storage.base import StorageProvider

logger = logging.getLogger(__name__)

# Fallback store for offline test execution when MinIO server is unavailable
_memory_storage_store: dict[str, bytes] = {}


class MinIOStorageProvider(StorageProvider):
    """MinIO implementation of StorageProvider."""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket_name: str | None = None,
        secure: bool | None = None,
    ) -> None:
        settings = get_settings()
        self.endpoint = endpoint or settings.minio_endpoint
        self.access_key = access_key or settings.minio_access_key
        self.secret_key = secret_key or settings.minio_secret_key
        self.bucket_name = bucket_name or settings.minio_bucket_name
        self.secure = secure if secure is not None else settings.minio_use_ssl

        self.client: Any = None
        self._is_online: bool = False
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize MinIO client and ensure target bucket exists."""
        if not MINIO_AVAILABLE or Minio is None:
            self._is_online = False
            logger.info("MinIO package not installed, using in-memory storage fallback")
            return

        try:
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
            self._is_online = True
            logger.info("MinIO storage provider initialized", extra={"bucket": self.bucket_name})
        except Exception as exc:
            self._is_online = False
            logger.warning(
                "MinIO server connection failed, using in-memory storage fallback: %s",
                str(exc),
            )

    async def upload(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file content to MinIO or memory store."""
        if self._is_online and self.client:
            try:
                data_stream = io.BytesIO(file_data)
                self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    data=data_stream,
                    length=len(file_data),
                    content_type=content_type,
                )
                return f"{self.bucket_name}/{object_name}"
            except Exception as exc:
                logger.error("MinIO upload failed, falling back to memory store: %s", str(exc))

        # Memory store fallback
        _memory_storage_store[f"{self.bucket_name}/{object_name}"] = file_data
        return f"{self.bucket_name}/{object_name}"

    async def download(self, object_name: str) -> bytes:
        """Download file content from MinIO or memory store."""
        full_key = object_name if object_name.startswith(f"{self.bucket_name}/") else f"{self.bucket_name}/{object_name}"
        clean_key = object_name.replace(f"{self.bucket_name}/", "")

        if self._is_online and self.client:
            try:
                response = self.client.get_object(self.bucket_name, clean_key)
                content = response.read()
                response.close()
                response.release_conn()
                return content
            except Exception as exc:
                logger.warning("MinIO download error: %s", str(exc))

        if full_key in _memory_storage_store:
            return _memory_storage_store[full_key]
        if clean_key in _memory_storage_store:
            return _memory_storage_store[clean_key]
        raise FileNotFoundError(f"Object {object_name} not found in storage")

    async def delete(self, object_name: str) -> bool:
        """Delete object from MinIO or memory store."""
        full_key = object_name if object_name.startswith(f"{self.bucket_name}/") else f"{self.bucket_name}/{object_name}"
        clean_key = object_name.replace(f"{self.bucket_name}/", "")

        if self._is_online and self.client:
            try:
                self.client.remove_object(self.bucket_name, clean_key)
            except Exception as exc:
                logger.warning("MinIO delete error: %s", str(exc))

        _memory_storage_store.pop(full_key, None)
        _memory_storage_store.pop(clean_key, None)
        return True

    async def copy(self, source_object: str, dest_object: str) -> bool:
        """Copy object from source to destination."""
        content = await self.download(source_object)
        await self.upload(content, dest_object)
        return True

    async def move(self, source_object: str, dest_object: str) -> bool:
        """Move object from source to destination."""
        await self.copy(source_object, dest_object)
        await self.delete(source_object)
        return True

    async def exists(self, object_name: str) -> bool:
        """Check if object exists."""
        full_key = object_name if object_name.startswith(f"{self.bucket_name}/") else f"{self.bucket_name}/{object_name}"
        clean_key = object_name.replace(f"{self.bucket_name}/", "")

        if self._is_online and self.client:
            try:
                self.client.stat_object(self.bucket_name, clean_key)
                return True
            except S3Error:
                return False
            except Exception:
                pass

        return full_key in _memory_storage_store or clean_key in _memory_storage_store

    async def generate_presigned_url(
        self,
        object_name: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate presigned download URL."""
        clean_key = object_name.replace(f"{self.bucket_name}/", "")

        if self._is_online and self.client:
            try:
                url = self.client.presigned_get_object(
                    bucket_name=self.bucket_name,
                    object_name=clean_key,
                    expires=timedelta(seconds=expires_in),
                )
                return str(url)
            except Exception as exc:
                logger.warning("MinIO presigned URL error: %s", str(exc))

        # Mock presigned URL for fallback
        return f"http://{self.endpoint}/{self.bucket_name}/{clean_key}?expires={expires_in}&signature=mock_sig"

    async def list_files(self, prefix: str = "") -> list[str]:
        """List objects matching prefix."""
        if self._is_online and self.client:
            try:
                objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
                return [obj.object_name for obj in objects if obj.object_name]
            except Exception as exc:
                logger.warning("MinIO list files error: %s", str(exc))

        # Memory store listing
        results: list[str] = []
        for key in _memory_storage_store:
            clean_key = key.replace(f"{self.bucket_name}/", "")
            if clean_key.startswith(prefix):
                results.append(clean_key)
        return results
