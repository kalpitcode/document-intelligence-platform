"""
Unit Tests for Storage Provider
=================================
"""

from __future__ import annotations

import pytest

from app.core.storage.minio_provider import MinIOStorageProvider


@pytest.mark.asyncio
async def test_storage_provider_upload_download_delete() -> None:
    provider = MinIOStorageProvider(bucket_name="test-bucket")
    test_key = "documents/test_file.txt"
    test_content = b"Sample Document Storage Bytes"

    # Upload
    path = await provider.upload(test_content, test_key, "text/plain")
    assert "test-bucket" in path

    # Exists
    exists = await provider.exists(test_key)
    assert exists is True

    # Download
    downloaded = await provider.download(test_key)
    assert downloaded == test_content

    # Presigned URL
    url = await provider.generate_presigned_url(test_key, expires_in=1800)
    assert isinstance(url, str)
    assert len(url) > 0

    # Delete
    deleted = await provider.delete(test_key)
    assert deleted is True

    exists_after_delete = await provider.exists(test_key)
    assert exists_after_delete is False
