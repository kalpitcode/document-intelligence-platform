"""
Observability Background Tasks Module
======================================

Celery background worker tasks for periodic metrics aggregation, log cleanup,
health monitoring, and self-diagnostics.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.observability_tasks.run_periodic_diagnostics_task")
def run_periodic_diagnostics_task() -> dict[str, Any]:
    """Periodic Celery background task for system self-diagnostics."""
    from app.services.diagnostics_service import diagnostics_service

    logger.info("Triggering periodic system diagnostics worker task...")
    loop = asyncio.get_event_loop() if asyncio.get_event_loop().is_running() else asyncio.new_event_loop()
    report = loop.run_until_complete(diagnostics_service.run_diagnostics())
    return report.model_dump()


@celery_app.task(name="app.workers.tasks.observability_tasks.run_log_cleanup_task")
def run_log_cleanup_task() -> dict[str, Any]:
    """Periodic Celery task for log maintenance."""
    from app.services.diagnostics_service import diagnostics_service

    logger.info("Triggering log cleanup worker task...")
    loop = asyncio.get_event_loop() if asyncio.get_event_loop().is_running() else asyncio.new_event_loop()
    res = loop.run_until_complete(diagnostics_service.perform_log_cleanup())
    return res
