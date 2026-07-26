"""
Integration Tests for Document API Endpoints
==============================================
"""

from __future__ import annotations

import io

from httpx import AsyncClient
import pytest

from app.models.user import UserModel
from app.services.token_service import TokenService


@pytest.mark.asyncio
async def test_document_upload_download_version_flow(
    client: AsyncClient,
    test_user: UserModel,
) -> None:
    # 1. Login user to get access token
    token_service = TokenService()
    access_token = token_service.create_access_token(
        user_id=test_user.id,
        email=test_user.email,
        username=test_user.username,
        token_version=test_user.token_version,
        roles=["User"],
        permissions=[],
    )
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Upload Document
    pdf_bytes = b"%PDF-1.4 Enterprise Financial Statement 2026 BlackRock"
    files = {"file": ("report.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"visibility": "Private"}

    response = await client.post("/api/v1/documents/upload", headers=headers, files=files, data=data)
    assert response.status_code == 201
    res_json = response.json()
    assert res_json["success"] is True
    doc_id = res_json["data"]["id"]
    assert res_json["data"]["original_filename"] == "report.pdf"
    assert res_json["data"]["version"] == 1

    # 3. Get Document Details
    get_res = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == doc_id

    # 4. List Documents
    list_res = await client.get("/api/v1/documents", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["data"]["total"] >= 1

    # 5. Get Presigned Download URL
    dl_res = await client.get(f"/api/v1/documents/{doc_id}/download", headers=headers)
    assert dl_res.status_code == 200
    assert "download_url" in dl_res.json()["data"]

    # 6. Upload New Version
    v2_pdf_bytes = b"%PDF-1.4 Financial Statement 2026 Version 2 Amended"
    v2_files = {"file": ("report_v2.pdf", io.BytesIO(v2_pdf_bytes), "application/pdf")}
    v2_data = {"change_notes": "Amended figures in Q4"}

    v2_res = await client.post(f"/api/v1/documents/{doc_id}/versions", headers=headers, files=v2_files, data=v2_data)
    assert v2_res.status_code == 201
    assert v2_res.json()["data"]["version_number"] == 2

    # 7. List Version History
    vers_res = await client.get(f"/api/v1/documents/{doc_id}/versions", headers=headers)
    assert vers_res.status_code == 200
    assert len(vers_res.json()["data"]) == 2

    # 8. Soft Delete Document
    del_res = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_document_upload_invalid_file_rejected(
    client: AsyncClient,
    test_user: UserModel,
) -> None:
    token_service = TokenService()
    access_token = token_service.create_access_token(
        user_id=test_user.id,
        email=test_user.email,
        username=test_user.username,
        token_version=test_user.token_version,
        roles=["User"],
        permissions=[],
    )
    headers = {"Authorization": f"Bearer {access_token}"}

    # Upload executable file
    exe_bytes = b"MZ executable content"
    files = {"file": ("malicious.exe", io.BytesIO(exe_bytes), "application/octet-stream")}

    response = await client.post("/api/v1/documents/upload", headers=headers, files=files)
    assert response.status_code == 400
    assert "DOCUMENT_VALIDATION_ERROR" in response.text
