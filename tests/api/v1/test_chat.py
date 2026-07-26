"""
RAG Chat API Integration Tests Module
======================================

Integration tests for the /api/v1/chat endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestChatEndpoints:
    """Integration tests for RAG Chat API controllers."""

    async def test_chat_unauthenticated(self, client: AsyncClient) -> None:
        """Unauthenticated requests should return 401 Unauthorized."""
        response = await client.post(
            "/api/v1/chat",
            json={"question": "What is BlackRock's strategy?"},
        )
        assert response.status_code == 401

    async def test_chat_pipeline_flow(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Authenticated RAG chat execution flow test."""
        # 1. Post new chat question
        chat_payload = {
            "question": "What are BlackRock's assets under management?",
            "temperature": 0.0,
            "max_tokens": 500,
            "search_mode": "hybrid",
            "top_k": 5,
        }
        response = await client.post(
            "/api/v1/chat",
            json=chat_payload,
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Response text: {response.text}"
        data = response.json()["data"]

        assert "session_id" in data
        assert "message_id" in data
        assert "answer" in data
        assert "citations" in data
        assert "latency" in data
        assert "token_usage" in data
        session_id = data["session_id"]

        # 2. Get user chat sessions list
        sessions_res = await client.get("/api/v1/chat/sessions", headers=auth_headers)
        assert sessions_res.status_code == 200
        sessions_data = sessions_res.json()["data"]
        assert sessions_data["total"] >= 1
        assert any(s["id"] == session_id for s in sessions_data["items"])

        # 3. Get session detail & message history
        detail_res = await client.get(f"/api/v1/chat/{session_id}", headers=auth_headers)
        assert detail_res.status_code == 200
        detail_data = detail_res.json()["data"]
        assert detail_data["session"]["id"] == session_id
        assert len(detail_data["messages"]) >= 2  # user + assistant

        # 4. Continue existing chat session
        followup_res = await client.post(
            f"/api/v1/chat/{session_id}",
            json={"question": "Can you elaborate further?"},
            headers=auth_headers,
        )
        assert followup_res.status_code == 200
        followup_data = followup_res.json()["data"]
        assert followup_data["session_id"] == session_id

        # 5. Delete session
        delete_res = await client.delete(f"/api/v1/chat/{session_id}", headers=auth_headers)
        assert delete_res.status_code == 200
        assert delete_res.json()["data"]["deleted"] is True
