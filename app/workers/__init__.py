"""
Workers Package
================

Celery workers and task definitions for background processing.

Usage::

    # Start the worker
    celery -A app.workers.celery_app worker --loglevel=info

    # Enqueue a task from FastAPI
    from app.workers.celery_app import celery_app
    result = celery_app.send_task("app.workers.tasks.example_task", args=[...])
"""

from __future__ import annotations

from app.workers.celery_app import celery_app

__all__ = ["celery_app"]
