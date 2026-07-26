"""
Upload Session Service Module
==============================

Manages upload transaction sessions and progress tracking.
"""

from __future__ import annotations

from datetime import UTC, datetime
import uuid

from app.models.document import UploadSessionModel
from app.repositories.upload_repository import UploadRepository


class UploadService:
    """Service managing upload session lifecycles."""

    def __init__(self, upload_repo: UploadRepository) -> None:
        self.repo = upload_repo

    async def create_session(
        self,
        user_id: uuid.UUID,
        upload_id: str | None = None,
    ) -> UploadSessionModel:
        """Initialize a new upload transaction session."""
        tid = upload_id or f"up_{uuid.uuid4().hex[:16]}"
        session_data = {
            "upload_id": tid,
            "user_id": user_id,
            "status": "STARTED",
            "progress": 0,
        }
        return await self.repo.create(**session_data)

    async def update_progress(
        self,
        upload_id: str,
        progress: int,
        status: str = "UPLOADING",
    ) -> UploadSessionModel | None:
        """Update upload session progress percentage."""
        sess = await self.repo.get_by_upload_id(upload_id)
        if not sess:
            return None

        update_data = {"progress": max(0, min(100, progress)), "status": status}
        return await self.repo.update(sess, **update_data)

    async def complete_session(self, upload_id: str) -> UploadSessionModel | None:
        """Mark upload session as successfully completed."""
        sess = await self.repo.get_by_upload_id(upload_id)
        if not sess:
            return None

        return await self.repo.update(
            sess,
            status="COMPLETED",
            progress=100,
            completed_at=datetime.now(UTC),
        )

    async def fail_session(self, upload_id: str) -> UploadSessionModel | None:
        """Mark upload session as failed."""
        sess = await self.repo.get_by_upload_id(upload_id)
        if not sess:
            return None

        return await self.repo.update(sess, status="FAILED")
