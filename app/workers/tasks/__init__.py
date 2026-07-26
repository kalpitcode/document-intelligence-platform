"""
Celery Tasks Package
=====================

All Celery tasks are defined in modules within this package.
Tasks are automatically discovered by the Celery app via `autodiscover_tasks`.

No business tasks are implemented yet — this package serves as the
registration point for future task modules.

To add a new task:
1. Create a new module in this package (e.g., `document_tasks.py`).
2. Define tasks using the `@celery_app.task` decorator.
3. The task will be auto-discovered on worker startup.

Example::

    # app/workers/tasks/document_tasks.py
    from app.workers.celery_app import celery_app

    @celery_app.task(bind=True, max_retries=3)
    def process_document(self, document_id: str) -> dict:
        ...
"""
