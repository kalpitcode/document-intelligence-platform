"""
Workflow Scheduler Service Module
=================================

Service handling automated cron scheduling, evaluating trigger rules,
and initiating recurring workflow execution runs.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Evaluates active cron schedules and triggers pending workflow runs.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Sequence
import uuid

from app.models.workflow import WorkflowScheduleModel
from app.repositories.workflow_repository import WorkflowRepository

logger = logging.getLogger(__name__)


class WorkflowSchedulerService:
    """Service evaluating workflow cron schedules and calculating next run times."""

    def __init__(self, workflow_repo: WorkflowRepository) -> None:
        self.repo = workflow_repo

    async def evaluate_schedules_and_get_due(self) -> Sequence[WorkflowScheduleModel]:
        """Fetch active schedules that are due for automated execution."""
        schedules = await self.repo.list_active_schedules()
        due_schedules: list[WorkflowScheduleModel] = []
        now = datetime.utcnow()

        for sched in schedules:
            if not sched.enabled or not sched.workflow or not sched.workflow.is_active:
                continue

            if sched.next_run is None or sched.next_run <= now:
                due_schedules.append(sched)

        return due_schedules

    def calculate_next_run(self, cron_expression: str, base_time: datetime | None = None) -> datetime:
        """Calculate next run timestamp based on cron expression."""
        base = base_time or datetime.utcnow()
        try:
            from croniter import croniter
            iter_cron = croniter(cron_expression, base)
            return iter_cron.get_next(datetime)
        except Exception:
            # Fallback simple 24-hour interval if croniter is unavailable or format is simple
            return base + timedelta(hours=24)
