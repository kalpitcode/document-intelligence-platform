"""
Celery Application Factory
============================

Creates and configures the Celery application instance.

**Architectural Rationale:**
- Celery is configured via a factory function for testability.
- Broker (RabbitMQ) and backend (Redis) URLs come from settings.
- Task autodiscovery scans the `app.workers.tasks` package.
- Serialization uses JSON for interoperability and debuggability.
- Task-level settings (acks_late, reject_on_worker_lost) ensure
  at-least-once delivery semantics.

**Connection to the system:**
- Workers are started separately: `celery -A app.workers.celery_app worker`
- Tasks are defined in `app.workers.tasks.*` modules.
- The FastAPI app can enqueue tasks via `task.delay()` or `task.apply_async()`.
"""

from __future__ import annotations

import os

from celery import Celery


def create_celery_app() -> Celery:
    """
    Create and configure the Celery application.

    Returns:
        Configured Celery application instance.
    """
    # Import settings lazily to avoid circular imports at worker startup
    broker_url = os.getenv(
        "CELERY_BROKER_URL",
        "amqp://dip_user:change_me_in_production@localhost:5672//",
    )
    result_backend = os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/1",
    )

    app = Celery(
        "document_intelligence",
        broker=broker_url,
        backend=result_backend,
    )

    # --- Celery Configuration ---
    app.conf.update(
        # Serialization
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        # Timezone
        timezone="UTC",
        enable_utc=True,
        # Task execution
        task_track_started=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        # Result expiry
        result_expires=3600,  # 1 hour
        # Task routing (future)
        task_default_queue="default",
        task_default_exchange="default",
        task_default_routing_key="default",
        # Worker
        worker_max_tasks_per_child=1000,
        worker_max_memory_per_child=512000,  # 512 MB
        # Concurrency
        worker_concurrency=4,
    )

    # Autodiscover tasks in the tasks package
    app.autodiscover_tasks(["app.workers.tasks"])

    return app


# Module-level Celery application instance
celery_app = create_celery_app()
