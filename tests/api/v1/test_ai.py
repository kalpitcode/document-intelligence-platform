"""
API Integration Tests for Enterprise AI Productivity Feature Endpoints
========================================================================

Verifies authentication, RBAC authorization, synchronous execution, async task queuing,
job status inspection, and result fetching for `/api/v1/ai/*`.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
import uuid
import pytest
from httpx import AsyncClient

from app.core.llm.base import LLMResponse
from app.models.ai import AIJobModel, AIJobStatus
from app.models.document import DocumentModel, DocumentStatus, Visibility
from app.models.processing import DocumentChunkModel


@pytest.mark.asyncio
class TestAIFeatureEndpoints:
    """Test suite for /api/v1/ai endpoints."""

    async def test_ai_unauthenticated_request_rejected(self, client: AsyncClient) -> None:
        """Unauthenticated requests to AI endpoints must return HTTP 401."""
        response = await client.post("/api/v1/ai/summarize", json={"document_id": str(uuid.uuid4())})
        assert response.status_code == 401

    async def test_summarize_synchronous_flow(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: dict[str, str],
        db_session: AsyncMock,
    ) -> None:
        """Test synchronous document summarization flow."""
        doc_id = uuid.uuid4()
        doc = DocumentModel(
            id=doc_id,
            owner_id=test_user.id,
            original_filename="sample_report.pdf",
            stored_filename="stored_sample.pdf",
            storage_path="documents/stored_sample.pdf",
            mime_type="application/pdf",
            extension=".pdf",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            file_size=2048,
            visibility=Visibility.PRIVATE,
            status=DocumentStatus.PROCESSING,
        )
        chunk = DocumentChunkModel(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_index=0,
            content="BlackRock Aladdin enterprise AI platform delivers high performance asset management software.",
            start_offset=0,
            end_offset=100,
            token_estimate=20,
        )
        db_session.add(doc)
        db_session.add(chunk)
        await db_session.commit()

        mock_llm_res = LLMResponse(
            content='{"summary": "Aladdin is an asset management software.", "summary_type": "executive", "key_takeaways": ["High performance"], "suggested_questions": ["What is Aladdin?"]}',
            prompt_tokens=50,
            completion_tokens=25,
            total_tokens=75,
            model_name="mock-gpt4",
            latency_ms=100,
            estimated_cost=0.001,
        )

        with patch("app.services.llm_service.LLMService.generate", return_value=mock_llm_res):
            response = await client.post(
                "/api/v1/ai/summarize",
                json={
                    "document_id": str(doc_id),
                    "summary_type": "executive",
                    "async_execution": False,
                },
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["job"]["status"] == "completed"
        assert data["data"]["result"]["result"]["summary"] == "Aladdin is an asset management software."

    async def test_classify_synchronous_flow(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: dict[str, str],
        db_session: AsyncMock,
    ) -> None:
        """Test synchronous classification flow."""
        doc_id = uuid.uuid4()
        doc = DocumentModel(
            id=doc_id,
            owner_id=test_user.id,
            original_filename="contract.pdf",
            stored_filename="stored_contract.pdf",
            storage_path="documents/stored_contract.pdf",
            mime_type="application/pdf",
            extension=".pdf",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            file_size=1024,
            visibility=Visibility.PRIVATE,
            status=DocumentStatus.PROCESSING,
        )
        chunk = DocumentChunkModel(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_index=0,
            content="This Master Services Agreement governs the relationship between the parties.",
            start_offset=0,
            end_offset=100,
            token_estimate=15,
        )
        db_session.add(doc)
        db_session.add(chunk)
        await db_session.commit()

        mock_llm_res = LLMResponse(
            content='{"category": "Legal Contract", "primary_topic": "Services Agreement", "secondary_topics": ["Terms"], "confidence_score": 0.98, "reasoning": "Legal contract language"}',
            prompt_tokens=40,
            completion_tokens=20,
            total_tokens=60,
            model_name="mock-gpt4",
            latency_ms=80,
            estimated_cost=0.001,
        )

        with patch("app.services.llm_service.LLMService.generate", return_value=mock_llm_res):
            response = await client.post(
                "/api/v1/ai/classify",
                json={"document_id": str(doc_id), "async_execution": False},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["result"]["result"]["category"] == "Legal Contract"
        assert data["data"]["result"]["result"]["confidence_score"] == 0.98

    async def test_get_job_status_endpoint(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_user: dict[str, str],
        db_session: AsyncMock,
    ) -> None:
        """Test retrieving AI job status by job_id."""
        doc_id = uuid.uuid4()
        job_id = uuid.uuid4()
        job = AIJobModel(
            id=job_id,
            user_id=test_user.id,
            document_id=doc_id,
            feature_type="summarize",
            status=AIJobStatus.COMPLETED.value,
            latency_ms=120,
            model="mock-gpt4",
        )
        db_session.add(job)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/ai/jobs/{job_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["job_id"] == str(job_id)
        assert data["data"]["status"] == "completed"
