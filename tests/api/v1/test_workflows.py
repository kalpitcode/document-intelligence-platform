"""
Integration & API End-to-End Tests for Workflow Engine Endpoints
================================================================

Tests REST API endpoints:
- POST /api/v1/workflows
- GET /api/v1/workflows
- GET /api/v1/workflows/{id}
- POST /api/v1/workflows/{id}/execute
- GET /api/v1/workflows/{id}/runs
- GET /api/v1/workflows/runs/{run_id}
- POST /api/v1/workflows/{id}/cancel
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_workflows_unauthenticated_request_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/workflows")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_workflow_template_creation_and_execution_flow(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    # 1. Create Workflow Template
    create_payload = {
        "name": "Test End-to-End Document Intake Workflow",
        "description": "Multi-step automated OCR, Hybrid Search, and RAG Question answering pipeline",
        "version": 1,
        "definition": {
            "steps": [
                {
                    "name": "doc_intake",
                    "type": "DOCUMENT_PROCESSING",
                    "inputs": {"document_id": "00000000-0000-0000-0000-000000000001"},
                },
                {
                    "name": "embed_content",
                    "type": "EMBEDDING_GENERATION",
                    "depends_on": ["doc_intake"],
                    "inputs": {"text": "BlackRock Aladdin Enterprise RAG Intelligence"},
                },
                {
                    "name": "rag_answer",
                    "type": "RAG_QUESTION",
                    "depends_on": ["embed_content"],
                    "inputs": {"query": "What capabilities does the Aladdin RAG engine provide?"},
                },
                {
                    "name": "audit_notify",
                    "type": "NOTIFICATION_STUB",
                    "depends_on": ["rag_answer"],
                    "inputs": {"message": "Workflow completion notification audit log"},
                },
            ]
        },
    }

    resp = await client.post("/api/v1/workflows", json=create_payload, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    template_data = body["data"]
    template_id = template_data["id"]
    assert template_data["name"] == create_payload["name"]

    # 2. List Workflow Templates
    list_resp = await client.get("/api/v1/workflows", headers=auth_headers)
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["data"]["total"] >= 1

    # 3. Get Workflow Template Detail
    detail_resp = await client.get(f"/api/v1/workflows/{template_id}", headers=auth_headers)
    assert detail_resp.status_code == 200

    # 4. Execute Workflow Template (Synchronously for immediate test assertion)
    exec_payload = {
        "inputs": {"document_id": "00000000-0000-0000-0000-000000000001", "query": "Test Aladdin RAG"},
        "run_async": False,
    }
    exec_resp = await client.post(f"/api/v1/workflows/{template_id}/execute", json=exec_payload, headers=auth_headers)
    assert exec_resp.status_code == 202
    exec_body = exec_resp.json()
    run_data = exec_body["data"]
    run_id = run_data["id"]
    assert run_data["status"] == "COMPLETED"
    assert len(run_data["steps"]) == 4

    # 5. List Runs for Template
    runs_resp = await client.get(f"/api/v1/workflows/{template_id}/runs", headers=auth_headers)
    assert runs_resp.status_code == 200
    runs_body = runs_resp.json()
    assert runs_body["data"]["total"] >= 1

    # 6. Get Run Detail
    run_detail_resp = await client.get(f"/api/v1/workflows/runs/{run_id}", headers=auth_headers)
    assert run_detail_resp.status_code == 200
    run_detail_body = run_detail_resp.json()
    assert run_detail_body["data"]["id"] == run_id
    assert run_detail_body["data"]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_workflow_cancellation_flow(
    client: AsyncClient,
    auth_headers: dict[str, str],
    mocker: Any = None,
) -> None:
    from unittest.mock import patch

    # Create template
    create_payload = {
        "name": "Cancellation Test Workflow",
        "definition": {
            "steps": [
                {"name": "step1", "type": "NOTIFICATION_STUB"}
            ]
        },
    }
    resp = await client.post("/api/v1/workflows", json=create_payload, headers=auth_headers)
    template_id = resp.json()["data"]["id"]

    # Trigger Async Run with mocked Celery delay
    with patch("app.api.v1.endpoints.workflows.execute_workflow_task.delay"):
        exec_resp = await client.post(f"/api/v1/workflows/{template_id}/execute", json={"run_async": True}, headers=auth_headers)
        run_id = exec_resp.json()["data"]["id"]

        # Cancel Run
        cancel_resp = await client.post(f"/api/v1/workflows/runs/{run_id}/cancel", headers=auth_headers)
        if cancel_resp.status_code == 404:
            cancel_resp = await client.post(f"/api/v1/workflows/{run_id}/cancel", headers=auth_headers)
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["data"]["status"] == "CANCELLED"
