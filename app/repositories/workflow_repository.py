"""
Workflow Repository Module
==========================

Repository pattern implementation for Workflow templates, runs, steps, events, and schedules.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Encapsulates database CRUD operations and query logic.
- Async SQLAlchemy 2.0 query execution with proper eager-loading and transaction management.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence
import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import (
    WorkflowEventModel,
    WorkflowRunModel,
    WorkflowScheduleModel,
    WorkflowStepModel,
    WorkflowTemplateModel,
)
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class WorkflowRepository(BaseRepository[WorkflowTemplateModel]):
    """Repository handling workflow entities persistence and querying."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WorkflowTemplateModel, session)

    # --- Workflow Templates ---

    async def create_template(
        self,
        name: str,
        definition_json: dict[str, Any],
        owner_id: uuid.UUID,
        description: str | None = None,
        version: int = 1,
        is_active: bool = True,
    ) -> WorkflowTemplateModel:
        """Create and persist a new workflow template."""
        template = WorkflowTemplateModel(
            id=uuid.uuid4(),
            name=name,
            description=description,
            version=version,
            is_active=is_active,
            definition_json=definition_json,
            owner_id=owner_id,
        )
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def get_template_by_id(
        self,
        template_id: uuid.UUID,
        include_schedules: bool = False,
    ) -> WorkflowTemplateModel | None:
        """Retrieve workflow template by primary key ID."""
        stmt = select(WorkflowTemplateModel).where(WorkflowTemplateModel.id == template_id)
        if include_schedules:
            stmt = stmt.options(selectinload(WorkflowTemplateModel.schedules))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        owner_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WorkflowTemplateModel], int]:
        """List workflow templates with optional user ownership and status filters."""
        stmt = select(WorkflowTemplateModel)
        count_stmt = select(func.count()).select_from(WorkflowTemplateModel)

        if owner_id is not None:
            stmt = stmt.where(WorkflowTemplateModel.owner_id == owner_id)
            count_stmt = count_stmt.where(WorkflowTemplateModel.owner_id == owner_id)
        if is_active is not None:
            stmt = stmt.where(WorkflowTemplateModel.is_active == is_active)
            count_stmt = count_stmt.where(WorkflowTemplateModel.is_active == is_active)

        stmt = stmt.order_by(WorkflowTemplateModel.created_at.desc()).offset(skip).limit(limit)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one() or 0

        items_res = await self.session.execute(stmt)
        items = items_res.scalars().all()

        return items, total

    async def update_template(
        self,
        template_id: uuid.UUID,
        **kwargs: Any,
    ) -> WorkflowTemplateModel | None:
        """Update fields of an existing workflow template."""
        template = await self.get_template_by_id(template_id)
        if not template:
            return None

        for key, value in kwargs.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)

        await self.session.flush()
        await self.session.refresh(template)
        return template

    # --- Workflow Runs ---

    async def create_run(
        self,
        workflow_id: uuid.UUID,
        trigger_type: str = "MANUAL",
        initiated_by: uuid.UUID | None = None,
    ) -> WorkflowRunModel:
        """Create a new workflow run execution record."""
        run = WorkflowRunModel(
            id=uuid.uuid4(),
            workflow_id=workflow_id,
            status="PENDING",
            trigger_type=trigger_type,
            initiated_by=initiated_by,
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run_by_id(
        self,
        run_id: uuid.UUID,
        include_steps: bool = True,
        include_events: bool = False,
    ) -> WorkflowRunModel | None:
        """Retrieve workflow run details by ID."""
        stmt = select(WorkflowRunModel).where(WorkflowRunModel.id == run_id)
        if include_steps:
            stmt = stmt.options(selectinload(WorkflowRunModel.steps))
        if include_events:
            stmt = stmt.options(selectinload(WorkflowRunModel.events))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_runs(
        self,
        workflow_id: uuid.UUID | None = None,
        initiated_by: uuid.UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WorkflowRunModel], int]:
        """List workflow execution runs with status and ownership filters."""
        stmt = select(WorkflowRunModel).options(selectinload(WorkflowRunModel.steps))
        count_stmt = select(func.count()).select_from(WorkflowRunModel)

        if workflow_id is not None:
            stmt = stmt.where(WorkflowRunModel.workflow_id == workflow_id)
            count_stmt = count_stmt.where(WorkflowRunModel.workflow_id == workflow_id)
        if initiated_by is not None:
            stmt = stmt.where(WorkflowRunModel.initiated_by == initiated_by)
            count_stmt = count_stmt.where(WorkflowRunModel.initiated_by == initiated_by)
        if status is not None:
            stmt = stmt.where(WorkflowRunModel.status == status)
            count_stmt = count_stmt.where(WorkflowRunModel.status == status)

        stmt = stmt.order_by(WorkflowRunModel.created_at.desc()).offset(skip).limit(limit)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one() or 0

        items_res = await self.session.execute(stmt)
        items = items_res.scalars().all()

        return items, total

    async def update_run(
        self,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> WorkflowRunModel | None:
        """Update workflow run status, metrics, or error message."""
        run = await self.get_run_by_id(run_id, include_steps=False)
        if not run:
            return None

        for key, value in kwargs.items():
            if hasattr(run, key):
                setattr(run, key, value)

        await self.session.flush()
        await self.session.refresh(run)
        return run

    # --- Workflow Steps ---

    async def create_step(
        self,
        workflow_run_id: uuid.UUID,
        step_name: str,
        step_type: str,
        execution_order: int = 0,
        step_metadata: dict[str, Any] | None = None,
    ) -> WorkflowStepModel:
        """Create and record a workflow step instance."""
        step = WorkflowStepModel(
            id=uuid.uuid4(),
            workflow_run_id=workflow_run_id,
            step_name=step_name,
            step_type=step_type,
            status="PENDING",
            retry_count=0,
            execution_order=execution_order,
            step_metadata=step_metadata or {},
        )
        self.session.add(step)
        await self.session.flush()
        await self.session.refresh(step)
        return step

    async def update_step(
        self,
        step_id: uuid.UUID,
        **kwargs: Any,
    ) -> WorkflowStepModel | None:
        """Update workflow step state, timing, or output metadata."""
        stmt = select(WorkflowStepModel).where(WorkflowStepModel.id == step_id)
        res = await self.session.execute(stmt)
        step = res.scalar_one_or_none()
        if not step:
            return None

        for key, value in kwargs.items():
            if hasattr(step, key):
                setattr(step, key, value)

        await self.session.flush()
        await self.session.refresh(step)
        return step

    # --- Workflow Events ---

    async def create_event(
        self,
        workflow_run_id: uuid.UUID,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> WorkflowEventModel:
        """Publish and store audit telemetry event for workflow run."""
        event = WorkflowEventModel(
            id=uuid.uuid4(),
            workflow_run_id=workflow_run_id,
            event_type=event_type,
            payload=payload or {},
        )
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    # --- Workflow Schedules ---

    async def create_schedule(
        self,
        workflow_id: uuid.UUID,
        cron_expression: str,
        timezone: str = "UTC",
        enabled: bool = True,
    ) -> WorkflowScheduleModel:
        """Register a cron schedule rule for a workflow template."""
        schedule = WorkflowScheduleModel(
            id=uuid.uuid4(),
            workflow_id=workflow_id,
            cron_expression=cron_expression,
            timezone=timezone,
            enabled=enabled,
        )
        self.session.add(schedule)
        await self.session.flush()
        await self.session.refresh(schedule)
        return schedule

    async def list_active_schedules(self) -> Sequence[WorkflowScheduleModel]:
        """List all active workflow cron schedules."""
        stmt = (
            select(WorkflowScheduleModel)
            .where(WorkflowScheduleModel.enabled.is_(True))
            .options(selectinload(WorkflowScheduleModel.workflow))
        )
        res = await self.session.execute(stmt)
        return res.scalars().all()
