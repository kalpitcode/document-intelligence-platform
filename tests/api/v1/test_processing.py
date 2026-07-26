"""
Integration Tests for Document Processing & OCR Controllers
============================================================
"""

from __future__ import annotations

import io
from httpx import AsyncClient
import pytest

from app.models.user import UserModel
from app.services.token_service import TokenService


@pytest.mark.asyncio
async def test_document_processing_pipeline_flow(
    client: AsyncClient,
    test_user: UserModel,
) -> None:
    token_service = TokenService()
    access_token = token_service.create_access_token(
        user_id=test_user.id,
        email=test_user.email,
        username=test_user.username,
        token_version=test_user.token_version,
        roles=["ADMIN"],
        permissions=[],
    )
    headers = {"Authorization": f"Bearer {access_token}"}

    # 1. Upload a valid document first
    pdf_bytes = b"Plain text financial report content for BlackRock Aladdin platform analysis."
    files = {"file": ("financial_analysis.txt", io.BytesIO(pdf_bytes), "text/plain")}

    upload_res = await client.post("/api/v1/documents/upload", headers=headers, files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["data"]["id"]

    # 2. Trigger Document Processing
    proc_res = await client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)
    assert proc_res.status_code == 202
    assert proc_res.json()["success"] is True

    # 3. Check Processing Job Status
    status_res = await client.get(f"/api/v1/documents/{doc_id}/processing-status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["data"]["status"] == "Completed"

    # 4. Fetch Extracted Document Content
    content_res = await client.get(f"/api/v1/documents/{doc_id}/content", headers=headers)
    assert content_res.status_code == 200
    c_data = content_res.json()["data"]
    assert "BlackRock Aladdin" in c_data["clean_text"]
    assert c_data["word_count"] > 0
    assert c_data["language"] == "en"

    # 5. Fetch Paginated Chunks
    chunks_res = await client.get(f"/api/v1/documents/{doc_id}/chunks", headers=headers)
    assert chunks_res.status_code == 200
    ch_data = chunks_res.json()["data"]
    assert ch_data["total"] >= 1
    assert len(ch_data["items"]) >= 1
    assert ch_data["items"][0]["chunk_index"] == 0

    # 6. Fetch Tables (empty for text file)
    tables_res = await client.get(f"/api/v1/documents/{doc_id}/tables", headers=headers)
    assert tables_res.status_code == 200
    assert isinstance(tables_res.json()["data"], list)

    # 7. Fetch Images (empty for text file)
    images_res = await client.get(f"/api/v1/documents/{doc_id}/images", headers=headers)
    assert images_res.status_code == 200
    assert isinstance(images_res.json()["data"], list)

    # 8. Trigger Reprocessing
    reproc_res = await client.post(f"/api/v1/documents/{doc_id}/reprocess", headers=headers)
    assert reproc_res.status_code == 202
    assert reproc_res.json()["success"] is True
