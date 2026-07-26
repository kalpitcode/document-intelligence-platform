"""
Integration Tests for Search & Knowledge Engine Endpoints
==========================================================
"""

from __future__ import annotations

import io
from httpx import AsyncClient
import pytest

from unittest.mock import MagicMock, patch

from app.models.user import UserModel
from app.services.token_service import TokenService


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.search.reindex_documents_task")
async def test_search_api_endpoints_flow(
    mock_reindex_task: MagicMock,
    client: AsyncClient,
    test_user: UserModel,
) -> None:
    mock_task_res = MagicMock()
    mock_task_res.id = "mock-task-id-12345"
    mock_reindex_task.delay.return_value = mock_task_res
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

    # 1. Upload and Process document to index into knowledge engine
    pdf_bytes = b"BlackRock Aladdin asset risk management portfolio analytics report."
    files = {"file": ("aladdin_report.txt", io.BytesIO(pdf_bytes), "text/plain")}

    upload_res = await client.post("/api/v1/documents/upload", headers=headers, files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["data"]["id"]

    proc_res = await client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)
    assert proc_res.status_code == 202

    # 2. GET Active Embedding Models
    models_res = await client.get("/api/v1/search/models", headers=headers)
    assert models_res.status_code == 200
    assert models_res.json()["success"] is True
    assert len(models_res.json()["data"]) >= 1
    assert "sentence-transformers" in models_res.json()["data"][0]["provider"] or "all-MiniLM" in models_res.json()["data"][0]["name"]

    # 3. POST /api/v1/search (Hybrid search)
    search_body = {
        "query": "Aladdin risk management analytics",
        "query_type": "hybrid",
        "top_k": 5,
    }
    search_res = await client.post("/api/v1/search", headers=headers, json=search_body)
    assert search_res.status_code == 200, f"Search failed with detail: {search_res.json()}"
    s_data = search_res.json()["data"]
    assert s_data["query"] == "Aladdin risk management analytics"
    assert s_data["query_type"] == "hybrid"
    assert isinstance(s_data["results"], list)

    # 4. GET /api/v1/search/history
    history_res = await client.get("/api/v1/search/history", headers=headers)
    assert history_res.status_code == 200
    h_data = history_res.json()["data"]
    assert h_data["total"] >= 1, f"History total was {h_data}"
    assert len(h_data["items"]) >= 1
    assert any(item["query"] == "Aladdin risk management analytics" for item in h_data["items"])

    # 5. POST /api/v1/search/reindex
    reindex_body = {"document_id": doc_id}
    reindex_res = await client.post("/api/v1/search/reindex", headers=headers, json=reindex_body)
    assert reindex_res.status_code == 202, f"Reindex failed: {reindex_res.json()}"
    assert reindex_res.json()["data"]["document_id"] == doc_id
