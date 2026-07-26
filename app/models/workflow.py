"""
Workflow Engine Database Models Module
=======================================

SQLAlchemy ORM models for the Enterprise Workflow Automation Engine.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Stores versioned workflow templates, execution run histories, step telemetry, event logs, and schedules.
- JSON/JSONB schema flexibility for workflow step definitions and step metadata.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import UserModel


class WorkflowTemplateModel(Base, UUIDMixin, TimestampMixin):
    """
    Workflow Template Entity.

    Defines a versioned, reusable multi-step workflow template.
    """

    __tablename__ = "workflow_templates"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Name of the workflow template",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Human-readable description of workflow objectives",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Incremental version number",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Whether template is enabled for execution",
    )
    definition_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        doc="JSON structure defining steps, connections, conditions, and retry policies",
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User ID of the template owner",
    )

    # Relationships
    owner: Mapped[UserModel] = relationship("UserModel", foreign_keys=[owner_id])
    runs: Mapped[list[WorkflowRunModel]] = relationship(
        "WorkflowRunModel",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )
    schedules: Mapped[list[WorkflowScheduleModel]] = relationship(
        "WorkflowScheduleModel",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_workflow_templates_owner_active", "owner_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowTemplateModel(id={self.id}, name='{self.name}', v={self.version})>"


class WorkflowRunModel(Base, UUIDMixin, TimestampMixin):
    """
    Workflow Run Entity.

    Represents an active or historical execution instance of a workflow template.
    """

    __tablename__ = "workflow_runs"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated Workflow Template ID",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        index=True,
        doc="Execution status: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when workflow run execution began",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when workflow run execution finished",
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Total execution time in milliseconds",
    )
    trigger_type: Mapped[str] = mapped_column(
        String(50),
        default="MANUAL",
        nullable=False,
        doc="Trigger mechanism: MANUAL, SCHEDULED, EVENT",
    )
    initiated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User ID initiating execution",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Top-level error message if execution failed",
    )

    # Relationships
    workflow: Mapped[WorkflowTemplateModel] = relationship("WorkflowTemplateModel", back_populates="runs")
    user: Mapped[UserModel | None] = relationship("UserModel", foreign_keys=[initiated_by])
    steps: Mapped[list[WorkflowStepModel]] = relationship(
        "WorkflowStepModel",
        back_populates="workflow_run",
        cascade="all, delete-orphan",
        order_by="WorkflowStepModel.execution_order",
    )
    events: Mapped[list[WorkflowEventModel]] = relationship(
        "WorkflowEventModel",
        back_populates="workflow_run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_workflow_runs_workflow_status", "workflow_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowRunModel(id={self.id}, status='{self.status}', trigger='{self.trigger_type}')>"


class WorkflowStepModel(Base, UUIDMixin, TimestampMixin):
    """
    Workflow Step Execution Entity.

    Records single step telemetry, retry attempts, inputs/outputs, and step status.
    """

    __tablename__ = "workflow_steps"

    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Parent Workflow Run ID",
    )
    step_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Unique step name within workflow definition",
    )
    step_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of step (DOCUMENT_PROCESSING, HYBRID_SEARCH, RAG_QUESTION, etc.)",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        index=True,
        doc="Step execution status: PENDING, RUNNING, COMPLETED, FAILED, SKIPPED",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Step start timestamp",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Step completion timestamp",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of retries executed for this step",
    )
    execution_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Step sequence index in run execution sequence",
    )
    step_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Step execution inputs, outputs, conditions, and error details",
    )

    # Relationships
    workflow_run: Mapped[WorkflowRunModel] = relationship("WorkflowRunModel", back_populates="steps")

    __table_args__ = (
        Index("ix_workflow_steps_run_order", "workflow_run_id", "execution_order"),
    )

    def __repr__(self) -> str:
        return f"<WorkflowStepModel(id={self.id}, name='{self.step_name}', status='{self.status}')>"


class WorkflowEventModel(Base, UUIDMixin):
    """
    Workflow Audit Telemetry Event Entity.

    Records audit trail events during workflow execution lifecycle.
    """

    __tablename__ = "workflow_events"

    workflow_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated Workflow Run ID",
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Event name: WorkflowStarted, WorkflowStepStarted, WorkflowStepCompleted, etc.",
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Audit details and context payload",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="Event occurrence timestamp",
    )

    # Relationships
    workflow_run: Mapped[WorkflowRunModel] = relationship("WorkflowRunModel", back_populates="events")

    def __repr__(self) -> str:
        return f"<WorkflowEventModel(id={self.id}, event='{self.event_type}')>"


class WorkflowScheduleModel(Base, UUIDMixin, TimestampMixin):
    """
    Workflow Schedule Entity.

    Defines cron schedule rules for recurring automated workflow runs.
    """

    __tablename__ = "workflow_schedules"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated Workflow Template ID",
    )
    cron_expression: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Cron schedule pattern (e.g., '0 0 * * *')",
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False,
        doc="Timezone identifier for schedule evaluation",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Whether active scheduler triggers this rule",
    )
    next_run: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Calculated next execution timestamp",
    )
    last_run: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last automated run trigger",
    )

    # Relationships
    workflow: Mapped[WorkflowTemplateModel] = relationship("WorkflowTemplateModel", back_populates="schedules")

    def __repr__(self) -> str:
        return f"<WorkflowScheduleModel(id={self.id}, cron='{self.cron_expression}', enabled={self.enabled})>"
