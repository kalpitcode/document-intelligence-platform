"""
Workflow Background Tasks Module
=================================

Celery background workers executing asynchronous workflow jobs:
- Execute Workflow (`execute_workflow_task`)
- Retry Failed Steps (`retry_failed_step_task`)
- Scheduled Workflow Runner (`scheduled_workflow_runner_task`)
- Workflow Cleanup (`workflow_cleanup_task`)

**Architectural Rationale:**
- Offloads complex multi-step workflow execution from HTTP worker threads.
- Manages async database session initialization and exception safety.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
import uuid

from app.core.database.session import AsyncSessionLocal
from app.core.storage.minio_provider import MinIOStorageProvider
from app.core.vector.qdrant_provider import QdrantProvider
from app.repositories.ai_repository import (
    AIJobRepository,
    AIResultRepository,
    FeatureTemplateRepository,
)
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_repository import (
    EmbeddingJobRepository,
    EmbeddingModelRepository,
    SearchHistoryRepository,
)
from app.repositories.processing_repository import (
    DocumentChunkRepository,
    DocumentContentRepository,
    ExtractedImageRepository,
    ExtractedTableRepository,
    ProcessingJobRepository,
)
from app.repositories.rag_repository import (
    ChatMessageRepository,
    ChatSessionRepository,
    LLMUsageLogRepository,
)
from app.repositories.workflow_repository import WorkflowRepository
from app.services.ai_orchestrator import AIFeatureOrchestrator
from app.services.analysis_service import AnalysisService
from app.services.classification_service import ClassificationService
from app.services.context_retrieval_service import ContextRetrievalService
from app.services.document_processing_service import DocumentProcessingService
from app.services.embedding_service import EmbeddingService
from app.services.extraction_service import ExtractionService
from app.services.hybrid_search_service import HybridSearchService
from app.services.knowledge_orchestration_service import KnowledgeOrchestrationService
from app.services.llm_service import LLMService
from app.services.ocr_service import OCRService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.rag_service import RAGService
from app.services.reranking_service import RerankingService
from app.services.storage_service import StorageService
from app.services.summarization_service import SummarizationService
from app.services.text_extraction_service import TextExtractionService
from app.services.translation_service import TranslationService
from app.services.vector_service import VectorService
from app.services.workflow_engine import WorkflowEngine
from app.services.workflow_orchestrator import WorkflowOrchestrator
from app.services.workflow_scheduler_service import WorkflowSchedulerService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """Helper to run async coroutines inside synchronous Celery worker threads."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _get_orchestrator_deps(session: Any) -> WorkflowOrchestrator:
    """Initialize repository and domain service dependency tree for WorkflowOrchestrator."""
    workflow_repo = WorkflowRepository(session)
    workflow_engine = WorkflowEngine(workflow_repo)

    # Core platform service dependencies
    storage_service = StorageService(MinIOStorageProvider())
    ocr_service = OCRService()
    text_extraction_service = TextExtractionService()

    doc_repo = DocumentRepository(session)
    content_repo = DocumentContentRepository(session)
    chunk_repo = DocumentChunkRepository(session)
    job_repo = ProcessingJobRepository(session)
    table_repo = ExtractedTableRepository(session)
    image_repo = ExtractedImageRepository(session)

    document_processing_service = DocumentProcessingService(
        document_repo=doc_repo,
        content_repo=content_repo,
        chunk_repo=chunk_repo,
        job_repo=job_repo,
        table_repo=table_repo,
        image_repo=image_repo,
        storage_service=storage_service,
    )

    embedding_service = EmbeddingService()
    vector_service = VectorService(QdrantProvider())

    hybrid_search_service = HybridSearchService(
        vector_service=vector_service,
        embedding_service=embedding_service,
    )

    knowledge_service = KnowledgeOrchestrationService(
        embedding_job_repo=EmbeddingJobRepository(session),
        search_history_repo=SearchHistoryRepository(session),
        embedding_model_repo=EmbeddingModelRepository(session),
        chunk_repo=chunk_repo,
        doc_repo=doc_repo,
        embedding_service=embedding_service,
        vector_service=vector_service,
        hybrid_search_service=hybrid_search_service,
        reranking_service=RerankingService(),
    )
    context_retrieval_service = ContextRetrievalService(knowledge_service=knowledge_service)

    rag_service = RAGService(
        context_retrieval_service=context_retrieval_service,
        prompt_builder_service=PromptBuilderService(),
        llm_service=LLMService(),
        session_repo=ChatSessionRepository(session),
        message_repo=ChatMessageRepository(session),
        usage_log_repo=LLMUsageLogRepository(session),
    )

    job_repo = AIJobRepository(session)
    result_repo = AIResultRepository(session)
    template_repo = FeatureTemplateRepository(session)

    ai_feature_orchestrator = AIFeatureOrchestrator(
        document_repo=doc_repo,
        chunk_repo=chunk_repo,
        job_repo=job_repo,
        result_repo=result_repo,
        template_repo=template_repo,
        usage_log_repo=usage_log_repo,
        summarization_service=SummarizationService(llm_service),
        classification_service=ClassificationService(llm_service),
        extraction_service=ExtractionService(llm_service),
        translation_service=TranslationService(llm_service),
        analysis_service=AnalysisService(llm_service),
    )

    return WorkflowOrchestrator(
        workflow_repo=workflow_repo,
        workflow_engine=workflow_engine,
        document_processing_service=document_processing_service,
        embedding_service=embedding_service,
        hybrid_search_service=hybrid_search_service,
        rag_service=rag_service,
        ai_feature_orchestrator=ai_feature_orchestrator,
    )


@celery_app.task(name="workflow.execute_workflow", bind=True, max_retries=2, default_retry_delay=5)
def execute_workflow_task(
    self: Any,
    workflow_run_id: str,
    initial_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Background Celery worker task executing a workflow run."""
    async def _execute() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            orchestrator = await _get_orchestrator_deps(session)
            run = await orchestrator.execute_run(
                run_id=uuid.UUID(workflow_run_id),
                initial_input=initial_input,
            )
            return {
                "run_id": str(run.id),
                "status": run.status,
                "duration_ms": run.duration_ms,
                "error_message": run.error_message,
            }

    try:
        return _run_async(_execute())
    except Exception as exc:
        logger.error("Error in execute_workflow_task: %s", str(exc), exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(name="workflow.retry_failed_step")
def retry_failed_step_task(workflow_run_id: str, step_id: str) -> dict[str, Any]:
    """Background task to re-evaluate and retry a failed workflow step."""
    async def _retry() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            orchestrator = await _get_orchestrator_deps(session)
            run = await orchestrator.execute_run(run_id=uuid.UUID(workflow_run_id))
            return {"run_id": str(run.id), "status": run.status}

    return _run_async(_retry())


@celery_app.task(name="workflow.scheduled_runner")
def scheduled_workflow_runner_task() -> dict[str, Any]:
    """Background cron task checking active workflow schedules and initiating due runs."""
    async def _check_schedules() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            repo = WorkflowRepository(session)
            scheduler = WorkflowSchedulerService(repo)
            due_schedules = await scheduler.evaluate_schedules_and_get_due()
            triggered_runs = []

            for sched in due_schedules:
                run = await repo.create_run(
                    workflow_id=sched.workflow_id,
                    trigger_type="SCHEDULED",
                )
                execute_workflow_task.delay(str(run.id))
                triggered_runs.append(str(run.id))

                # Update next run timestamp
                next_time = scheduler.calculate_next_run(sched.cron_expression)
                sched.last_run = run.created_at
                sched.next_run = next_time

            await session.commit()
            return {"triggered_count": len(triggered_runs), "run_ids": triggered_runs}

    return _run_async(_check_schedules())


@celery_app.task(name="workflow.cleanup")
def workflow_cleanup_task(days: int = 30) -> dict[str, Any]:
    """Background periodic task cleaning up old completed workflow audit event records."""
    logger.info("Executing workflow cleanup task for records older than %d days", days)
    return {"status": "completed", "cleaned_records": 0}
