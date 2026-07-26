"""
AI Feature Repositories Module
================================

Repositories managing database operations for AIJobModel, AIResultModel, and FeatureTemplateModel.

Architectural Rationale:
- Extends `BaseRepository<T>` pattern.
- Asynchronous database queries with explicit ordering and filtering.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Sequence
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIFeatureType, AIJobModel, AIJobStatus, AIResultModel, FeatureTemplateModel
from app.repositories.base import BaseRepository


class AIJobRepository(BaseRepository[AIJobModel]):
    """Repository managing execution jobs for AI document intelligence tasks."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AIJobModel, session)

    async def create_job(
        self,
        user_id: uuid.UUID | str,
        document_id: uuid.UUID | str,
        feature_type: str | AIFeatureType,
        model: str | None = None,
    ) -> AIJobModel:
        """Create a new AIJob record in pending state."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        feat_str = feature_type.value if isinstance(feature_type, AIFeatureType) else str(feature_type)

        return await self.create(
            user_id=user_id,
            document_id=document_id,
            feature_type=feat_str,
            status=AIJobStatus.PENDING.value,
            model=model,
            retry_count=0,
            latency_ms=0,
        )

    async def get_by_id_and_user(
        self,
        job_id: uuid.UUID | str,
        user_id: uuid.UUID | str,
    ) -> AIJobModel | None:
        """Get AI job by ID with user ownership check."""
        if isinstance(job_id, str):
            job_id = uuid.UUID(job_id)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        stmt = select(AIJobModel).where(
            AIJobModel.id == job_id,
            AIJobModel.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_status(
        self,
        job: AIJobModel,
        status: AIJobStatus | str,
        error_message: str | None = None,
        latency_ms: int = 0,
        model: str | None = None,
    ) -> AIJobModel:
        """Update job status, latency, model, and error message."""
        st_str = status.value if isinstance(status, AIJobStatus) else str(status)
        now = datetime.now(UTC)

        update_data: dict[str, Any] = {
            "status": st_str,
            "updated_at": now,
        }

        if st_str == AIJobStatus.PROCESSING.value:
            update_data["started_at"] = now
        elif st_str in (AIJobStatus.COMPLETED.value, AIJobStatus.FAILED.value):
            update_data["completed_at"] = now

        if latency_ms > 0:
            update_data["latency_ms"] = latency_ms
        if model:
            update_data["model"] = model
        if error_message:
            update_data["error_message"] = error_message
            update_data["retry_count"] = job.retry_count + 1

        return await self.update(job, **update_data)

    async def get_pending_or_failed_jobs(self, max_retries: int = 3, limit: int = 50) -> Sequence[AIJobModel]:
        """Fetch pending or failed jobs eligible for retries."""
        stmt = (
            select(AIJobModel)
            .where(
                (AIJobModel.status == AIJobStatus.PENDING.value)
                | ((AIJobModel.status == AIJobStatus.FAILED.value) & (AIJobModel.retry_count < max_retries))
            )
            .order_by(AIJobModel.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class AIResultRepository(BaseRepository[AIResultModel]):
    """Repository managing output payloads and metadata for AI features."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AIResultModel, session)

    async def create_result(
        self,
        document_id: uuid.UUID | str,
        feature_type: str | AIFeatureType,
        result: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        job_id: uuid.UUID | str | None = None,
    ) -> AIResultModel:
        """Store structured AI feature result."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)
        if isinstance(job_id, str):
            job_id = uuid.UUID(job_id)

        feat_str = feature_type.value if isinstance(feature_type, AIFeatureType) else str(feature_type)

        return await self.create(
            job_id=job_id,
            document_id=document_id,
            feature_type=feat_str,
            result=result,
            result_metadata=metadata or {},
        )

    async def get_latest_by_document_and_feature(
        self,
        document_id: uuid.UUID | str,
        feature_type: str | AIFeatureType,
    ) -> AIResultModel | None:
        """Fetch the most recent result for a given document and feature type."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        feat_str = feature_type.value if isinstance(feature_type, AIFeatureType) else str(feature_type)

        stmt = (
            select(AIResultModel)
            .where(
                AIResultModel.document_id == document_id,
                AIResultModel.feature_type == feat_str,
            )
            .order_by(AIResultModel.created_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()


class FeatureTemplateRepository(BaseRepository[FeatureTemplateModel]):
    """Repository managing versioned prompt templates for AI features."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FeatureTemplateModel, session)

    async def get_active_by_feature_name(self, feature_name: str) -> FeatureTemplateModel | None:
        """Get active prompt template for a feature."""
        stmt = select(FeatureTemplateModel).where(
            FeatureTemplateModel.feature_name == feature_name,
            FeatureTemplateModel.is_active == True,  # noqa: E712
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()
