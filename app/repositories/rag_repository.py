"""
RAG Engine Repositories Module
===============================

Repositories managing database persistence for ChatSessionModel, ChatMessageModel,
PromptTemplateModel, and LLMUsageLogModel.

Architectural Rationale:
- Extends `BaseRepository<T>` pattern.
- Implements async database queries with explicit ordering and filtering.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Sequence
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag import ChatMessageModel, ChatSessionModel, LLMUsageLogModel, PromptTemplateModel
from app.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSessionModel]):
    """Repository managing user RAG chat session threads."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ChatSessionModel, session)

    async def get_user_sessions(
        self,
        user_id: uuid.UUID | str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[ChatSessionModel], int]:
        """Fetch paginated chat sessions for a specific user ordered by last_message_at desc."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        stmt = (
            select(ChatSessionModel)
            .where(ChatSessionModel.user_id == user_id)
            .order_by(ChatSessionModel.last_message_at.desc())
        )

        # Count total
        count_stmt = select(func.count(ChatSessionModel.id)).where(ChatSessionModel.user_id == user_id)
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar_one_or_none() or 0

        # Page result
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def get_session_by_id_and_user(
        self,
        session_id: uuid.UUID | str,
        user_id: uuid.UUID | str,
    ) -> ChatSessionModel | None:
        """Fetch session by ID with user ownership check."""
        if isinstance(session_id, str):
            session_id = uuid.UUID(session_id)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        stmt = select(ChatSessionModel).where(
            ChatSessionModel.id == session_id,
            ChatSessionModel.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def touch_session(self, chat_session: ChatSessionModel, title: str | None = None) -> ChatSessionModel:
        """Update last_message_at timestamp and optional title."""
        now = datetime.now(UTC)
        update_data: dict[str, Any] = {"last_message_at": now, "updated_at": now}
        if title:
            update_data["title"] = title
        return await self.update(chat_session, **update_data)


class ChatMessageRepository(BaseRepository[ChatMessageModel]):
    """Repository managing individual chat messages within a session."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ChatMessageModel, session)

    async def get_session_messages(
        self,
        session_id: uuid.UUID | str,
        limit: int = 100,
    ) -> Sequence[ChatMessageModel]:
        """Fetch conversation messages for a chat session in chronological order."""
        if isinstance(session_id, str):
            session_id = uuid.UUID(session_id)

        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class PromptTemplateRepository(BaseRepository[PromptTemplateModel]):
    """Repository managing version-controlled enterprise system prompt templates."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PromptTemplateModel, session)

    async def get_active_by_name(self, name: str) -> PromptTemplateModel | None:
        """Retrieve active prompt template by unique template name."""
        stmt = select(PromptTemplateModel).where(
            PromptTemplateModel.name == name,
            PromptTemplateModel.is_active == True,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class LLMUsageLogRepository(BaseRepository[LLMUsageLogModel]):
    """Repository managing LLM consumption audit logs."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(LLMUsageLogModel, session)

    async def log_usage(
        self,
        user_id: uuid.UUID | str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost: float,
        latency_ms: int,
        prompt_template_name: str | None = None,
        prompt_version: str | None = None,
        retrieved_chunk_ids: list[str] | None = None,
        retrieval_scores: list[float] | None = None,
        retrieval_strategy: str | None = None,
    ) -> LLMUsageLogModel:
        """Create a new LLM usage audit log record with telemetry metadata."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        return await self.create(
            user_id=user_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            latency_ms=latency_ms,
            prompt_template_name=prompt_template_name,
            prompt_version=prompt_version,
            retrieved_chunk_ids=retrieved_chunk_ids,
            retrieval_scores=retrieval_scores,
            retrieval_strategy=retrieval_strategy,
        )
