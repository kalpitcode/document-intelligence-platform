"""
RAG Background Tasks Module
===========================

Celery worker tasks for RAG Engine operations:
- `cleanup_old_chat_sessions_task`: Purges inactive sessions.
- `refresh_prompt_templates_task`: Refreshes system prompt template cache.
- `aggregate_llm_usage_analytics_task`: Aggregates LLM usage telemetry metrics.

Architectural Rationale:
- Background asynchronous worker execution via Celery & Redis.
- Uses `AsyncSessionLocal` async context manager for safe database transactions outside HTTP requests.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
import structlog
from sqlalchemy import delete, func, select

from app.core.database.session import AsyncSessionLocal
from app.models.rag import ChatMessageModel, ChatSessionModel, LLMUsageLogModel, PromptTemplateModel
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="rag.cleanup_old_chat_sessions", bind=True, max_retries=3)
def cleanup_old_chat_sessions_task(self: Any, retention_days: int = 30) -> dict[str, Any]:
    """Purge chat sessions inactive for longer than retention_days."""
    async def _async_cleanup() -> int:
        async with AsyncSessionLocal() as session:
            cutoff = datetime.now(UTC) - timedelta(days=retention_days)
            stmt = delete(ChatSessionModel).where(ChatSessionModel.last_message_at < cutoff)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

    try:
        purged_count = asyncio.run(_async_cleanup())
        logger.info("Cleaned up inactive chat sessions", purged_count=purged_count, retention_days=retention_days)
        return {"status": "SUCCESS", "purged_count": purged_count}
    except Exception as exc:
        logger.error("Failed to cleanup old chat sessions", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="rag.refresh_prompt_templates", bind=True, max_retries=3)
def refresh_prompt_templates_task(self: Any) -> dict[str, Any]:
    """Pre-fetch active system prompt templates and log template status."""
    async def _async_refresh() -> list[str]:
        async with AsyncSessionLocal() as session:
            stmt = select(PromptTemplateModel).where(PromptTemplateModel.is_active == True)  # noqa: E712
            res = await session.execute(stmt)
            templates = res.scalars().all()
            return [t.name for t in templates]

    try:
        active_names = asyncio.run(_async_refresh())
        logger.info("Refreshed active prompt templates", active_templates=active_names)
        return {"status": "SUCCESS", "active_templates": active_names}
    except Exception as exc:
        logger.error("Failed to refresh prompt templates", error=str(exc))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="rag.aggregate_llm_usage_analytics", bind=True, max_retries=3)
def aggregate_llm_usage_analytics_task(self: Any) -> dict[str, Any]:
    """Aggregate token usage and cost metrics per user over the last 24 hours."""
    async def _async_aggregate() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            since = datetime.now(UTC) - timedelta(hours=24)
            stmt = select(
                func.count(LLMUsageLogModel.id).label("request_count"),
                func.sum(LLMUsageLogModel.total_tokens).label("total_tokens"),
                func.sum(LLMUsageLogModel.cost).label("total_cost"),
            ).where(LLMUsageLogModel.created_at >= since)
            
            res = await session.execute(stmt)
            row = res.first()
            return {
                "request_count": row.request_count or 0 if row else 0,
                "total_tokens": row.total_tokens or 0 if row else 0,
                "total_cost": round(float(row.total_cost or 0.0), 4) if row else 0.0,
            }

    try:
        analytics = asyncio.run(_async_aggregate())
        logger.info("Aggregated LLM usage analytics", analytics=analytics)
        return {"status": "SUCCESS", "analytics": analytics}
    except Exception as exc:
        logger.error("Failed to aggregate usage analytics", error=str(exc))
        raise self.retry(exc=exc, countdown=60)
