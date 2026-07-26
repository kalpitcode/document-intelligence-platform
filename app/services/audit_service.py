"""
Audit Service Module
=====================

Business service for recording security and compliance audit logs.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.core.logging.context import get_request_id
from app.repositories.audit_repository import AuditRepository
from app.utils.time import utc_now

logger = logging.getLogger(__name__)


class AuditService:
    """Service dedicated to security auditing and activity tracking."""

    def __init__(self, audit_repo: AuditRepository) -> None:
        self.audit_repo = audit_repo

    async def log_event(
        self,
        action: str,
        user_id: uuid.UUID | str | None = None,
        target_resource: str | None = None,
        status: str = "SUCCESS",
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Record a security audit log entry.
        """
        req_id = get_request_id()
        u_id = uuid.UUID(str(user_id)) if user_id else None

        await self.audit_repo.create(
            request_id=req_id,
            user_id=u_id,
            action=action,
            target_resource=target_resource,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=utc_now(),
            details=details or {},
        )

        logger.info(
            "Audit event logged: %s status=%s user_id=%s ip=%s",
            action,
            status,
            user_id,
            ip_address,
        )
