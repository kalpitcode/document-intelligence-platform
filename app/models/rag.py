"""
RAG Engine ORM Data Models Module
=================================

SQLAlchemy ORM models defining database tables for:
- `ChatSessionModel` (`chat_sessions`)
- `ChatMessageModel` (`chat_messages`)
- `PromptTemplateModel` (`prompt_templates`)
- `LLMUsageLogModel` (`llm_usage_logs`)

Architectural Rationale:
- Clean Architecture & SOLID principles.
- Strict foreign key constraints with indexed lookup columns.
- Preserves datetime timezone consistency and UUID primary keys.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database.base import Base, TimestampMixin, UUIDMixin

# Cross-DB JSON column support for SQLite and PostgreSQL
JSONColumn = JSON().with_variant(JSONB, "postgresql")


class ChatSessionModel(Base):
    """
    RAG Chat Session ORM Model.

    Represents a multi-turn conversation thread associated with a specific user.
    """

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="New Chat",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationships
    user: Mapped[Any] = relationship("UserModel", backref="chat_sessions")
    messages: Mapped[list[ChatMessageModel]] = relationship(
        "ChatMessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessageModel.created_at.asc()",
    )

    __table_args__ = (
        Index("ix_chat_sessions_user_last_msg", "user_id", "last_message_at"),
    )


class ChatMessageModel(Base):
    """
    RAG Chat Message ORM Model.

    Represents an individual user prompt or assistant response within a ChatSession.
    """

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,  # "user", "assistant", "system"
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    citations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONColumn,
        nullable=False,
        default=list,
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationship
    session: Mapped[ChatSessionModel] = relationship(
        "ChatSessionModel",
        back_populates="messages",
    )

    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )


class PromptTemplateModel(Base):
    """
    Prompt Template ORM Model.

    Version-controlled enterprise system prompts governing LLM behavior.
    """

    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )
    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="1.0.0",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class LLMUsageLogModel(Base):
    """
    LLM Usage Audit Log ORM Model.

    Tracks token consumption, execution cost, latency, and model metrics for observability.
    """

    __tablename__ = "llm_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    prompt_template_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        default="default_rag",
    )
    prompt_version: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        default="1.0.0",
    )
    retrieved_chunk_ids: Mapped[list[str] | None] = mapped_column(
        JSONColumn,
        nullable=True,
        default=list,
    )
    retrieval_scores: Mapped[list[float] | None] = mapped_column(
        JSONColumn,
        nullable=True,
        default=list,
    )
    retrieval_strategy: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        default="hybrid",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationship
    user: Mapped[Any] = relationship("UserModel", backref="llm_usage_logs")

    __table_args__ = (
        Index("ix_llm_usage_logs_user_created", "user_id", "created_at"),
    )
