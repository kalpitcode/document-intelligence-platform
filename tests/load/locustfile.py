"""
Locust Performance & Load Testing Suite
========================================

Executes enterprise load scenarios against platform API endpoints:
1. Health & Readiness Probes
2. Document Upload Workloads
3. Hybrid Search & Vector Query Workloads
4. RAG Conversational Queries
5. Orchestrated Workflow DAG Executions
"""

from __future__ import annotations

import json
from locust import HttpUser, between, task


class PlatformLoadUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def check_health_probes(self) -> None:
        self.client.get("/api/v1/health")
        self.client.get("/api/v1/health/live")
        self.client.get("/api/v1/health/ready")

    @task(2)
    def query_metrics_and_status(self) -> None:
        self.client.get("/api/v1/metrics")
        self.client.get("/api/v1/system/status")

    @task(2)
    def test_search_workload(self) -> None:
        payload = {
            "query": "financial earnings analysis BlackRock Q4",
            "search_type": "hybrid",
            "limit": 10,
        }
        self.client.post("/api/v1/search", json=payload)

    @task(1)
    def test_rag_query_workload(self) -> None:
        payload = {
            "message": "Summarize the primary risk factors mentioned in the quarterly report.",
            "top_k": 5,
        }
        self.client.post("/api/v1/chat/query", json=payload)

    @task(1)
    def test_workflow_execution_workload(self) -> None:
        payload = {
            "workflow_name": "Standard Ingestion DAG",
            "document_id": "doc-test-123",
        }
        self.client.post("/api/v1/workflows/execute", json=payload)
