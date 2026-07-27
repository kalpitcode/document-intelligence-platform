"""
Audit Trail Logging Service Module
====================================

Enterprise audit logging system capturing immutable audit trails for security,
compliance, and administrative actions.

**Architectural Rationale:**
- Implements audit logging across Authentication, Document Upload, OCR, Vector Embedding,
  Hybrid Search, RAG Queries, AI Features, Workflow Execution, and Administrative Actions.
- Formats structured JSON audit entries with timestamp, user_id, action, resource,
  client_ip, and status metadata.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any
import uuid

from app.core.logging.context import get_request_id, get_user_id
from app.core.logging.formatters import redact_sensitive_data

logger = logging.getLogger("audit_logger")


class AuditService:
    """Enterprise Audit Logging Service."""

    def record_event(
        self,
        category: str,
        action: str,
        resource_id: str | uuid.UUID | None = None,
        user_id: str | uuid.UUID | None = None,
        status: str = "SUCCESS",
        details: dict[str, Any] | None = None,
        client_ip: str | None = None,
    ) -> dict[str, Any]:
        """Record an immutable structured audit event."""
        resolved_user = user_id or get_user_id() or "anonymous"
        event = {
            "audit_id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "category": category.upper(),
            "action": action,
            "resource_id": str(resource_id) if resource_id else None,
            "user_id": str(resolved_user),
            "request_id": get_request_id(),
            "status": status,
            "client_ip": client_ip,
            "details": redact_sensitive_data(details or {}),
        }

        logger.info(
            f"AUDIT [{category}] {action} - Status: {status}",
            extra={"audit_event": event},
        )
        return event

    def log_auth(self, action: str, user_id: str | uuid.UUID, status: str = "SUCCESS", details: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.record_event("AUTHENTICATION", action, resource_id=str(user_id), user_id=user_id, status=status, details=details)

    def log_upload(self, document_id: str | uuid.UUID, file_name: str, file_size: int, status: str = "SUCCESS") -> dict[str, Any]:
        return self.record_event("DOCUMENT_UPLOAD", "UPLOAD", resource_id=document_id, status=status, details={"file_name": file_name, "file_size": file_size})

    def log_ocr(self, document_id: str | uuid.UUID, pages: int, status: str = "SUCCESS") -> dict[str, Any]:
        return self.record_event("OCR_PROCESSING", "EXTRACT_TEXT", resource_id=document_id, status=status, details={"pages": pages})

    def log_embedding(self, document_id: str | uuid.UUID, chunk_count: int, status: str = "SUCCESS") -> dict[str, Any]:
        return self.record_event("EMBEDDING_GENERATION", "GENERATE_VECTORS", resource_id=document_id, status=status, details={"chunks": chunk_count})

    def log_search(self, query: str, results_count: int, strategy: str = "hybrid") -> dict[str, Any]:
        return self.record_event("SEARCH", "EXECUTE_SEARCH", status="SUCCESS", details={"query_length": len(query), "results": results_count, "strategy": strategy})

    def log_rag(self, query: str, model: str, status: str = "SUCCESS") -> dict[str, Any]:
        return self.record_event("RAG_QUERY", "GENERATE_RESPONSE", status=status, details={"model": model, "query_length": len(query)})

    def log_ai_feature(self, feature_type: str, document_id: str | uuid.UUID, status: str = "SUCCESS") -> dict[str, Any]:
        return self.record_event("AI_FEATURE", feature_type.upper(), resource_id=document_id, status=status)

    def log_workflow(self, workflow_id: str | uuid.UUID, run_id: str | uuid.UUID, action: str, status: str = "SUCCESS") -> dict[str, Any]:
        return self.record_event("WORKFLOW", action, resource_id=run_id, status=status, details={"workflow_id": str(workflow_id)})

    def log_admin(self, action: str, target: str, status: str = "SUCCESS", details: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.record_event("ADMINISTRATIVE", action, resource_id=target, status=status, details=details)


audit_service = AuditService()
