"""
AI Feature Background Tasks Module
==================================

Celery background workers executing asynchronous document intelligence jobs for:
- Summarization
- Classification
- Entity & Action Item Extraction
- Translation
- Analysis
- Retrying Failed AI Jobs

Architectural Rationale:
- Offloads intensive LLM processing from HTTP request-response cycles.
- Manages async database session initialization and exception safety.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.database.session import AsyncSessionLocal
from app.models.ai import AIFeatureType
from app.repositories.ai_repository import AIJobRepository, AIResultRepository, FeatureTemplateRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.processing_repository import DocumentChunkRepository
from app.repositories.rag_repository import LLMUsageLogRepository
from app.services.ai_orchestrator import AIFeatureOrchestrator
from app.services.analysis_service import AnalysisService
from app.services.classification_service import ClassificationService
from app.services.extraction_service import ExtractionService
from app.services.llm_service import LLMService
from app.services.summarization_service import SummarizationService
from app.services.translation_service import TranslationService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """Helper to run async coroutines inside synchronous Celery worker threads."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _execute_ai_task(
    user_id: str,
    document_id: str,
    feature_type: str,
    kwargs: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Helper initializing dependencies and driving AIFeatureOrchestrator."""
    async with AsyncSessionLocal() as session:
        doc_repo = DocumentRepository(session)
        chunk_repo = DocumentChunkRepository(session)
        job_repo = AIJobRepository(session)
        result_repo = AIResultRepository(session)
        template_repo = FeatureTemplateRepository(session)
        usage_log_repo = LLMUsageLogRepository(session)

        llm_service = LLMService()
        summarization_service = SummarizationService(llm_service)
        classification_service = ClassificationService(llm_service)
        extraction_service = ExtractionService(llm_service)
        translation_service = TranslationService(llm_service)
        analysis_service = AnalysisService(llm_service)

        orchestrator = AIFeatureOrchestrator(
            document_repo=doc_repo,
            chunk_repo=chunk_repo,
            job_repo=job_repo,
            result_repo=result_repo,
            template_repo=template_repo,
            usage_log_repo=usage_log_repo,
            summarization_service=summarization_service,
            classification_service=classification_service,
            extraction_service=extraction_service,
            translation_service=translation_service,
            analysis_service=analysis_service,
        )

        job, result = await orchestrator.execute_feature(
            user_id=user_id,
            document_id=document_id,
            feature_type=feature_type,
            kwargs=kwargs or {},
            job_id=job_id,
        )

        return {
            "job_id": str(job.id),
            "result_id": str(result.id),
            "status": job.status,
            "latency_ms": job.latency_ms,
        }


@celery_app.task(name="ai.generate_summary", bind=True, max_retries=3, default_retry_delay=10)
def generate_summary_task(
    self: Any,
    user_id: str,
    document_id: str,
    summary_type: str = "executive",
    job_id: str | None = None,
) -> dict[str, Any]:
    """Background task to generate document summary."""
    try:
        return _run_async(
            _execute_ai_task(
                user_id=user_id,
                document_id=document_id,
                feature_type=AIFeatureType.SUMMARIZE.value,
                kwargs={"summary_type": summary_type},
                job_id=job_id,
            )
        )
    except Exception as exc:
        logger.error("Error in generate_summary_task: %s", str(exc))
        raise self.retry(exc=exc)


@celery_app.task(name="ai.run_classification", bind=True, max_retries=3, default_retry_delay=10)
def run_classification_task(
    self: Any,
    user_id: str,
    document_id: str,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Background task to run document classification."""
    try:
        return _run_async(
            _execute_ai_task(
                user_id=user_id,
                document_id=document_id,
                feature_type=AIFeatureType.CLASSIFY.value,
                job_id=job_id,
            )
        )
    except Exception as exc:
        logger.error("Error in run_classification_task: %s", str(exc))
        raise self.retry(exc=exc)


@celery_app.task(name="ai.extract_entities", bind=True, max_retries=3, default_retry_delay=10)
def extract_entities_task(
    self: Any,
    user_id: str,
    document_id: str,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Background task to extract entities, keywords, and action items."""
    try:
        return _run_async(
            _execute_ai_task(
                user_id=user_id,
                document_id=document_id,
                feature_type=AIFeatureType.EXTRACT.value,
                job_id=job_id,
            )
        )
    except Exception as exc:
        logger.error("Error in extract_entities_task: %s", str(exc))
        raise self.retry(exc=exc)


@celery_app.task(name="ai.translate_document", bind=True, max_retries=3, default_retry_delay=10)
def translate_document_task(
    self: Any,
    user_id: str,
    document_id: str,
    target_language: str,
    source_language: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Background task to translate document."""
    try:
        return _run_async(
            _execute_ai_task(
                user_id=user_id,
                document_id=document_id,
                feature_type=AIFeatureType.TRANSLATE.value,
                kwargs={"target_language": target_language, "source_language": source_language},
                job_id=job_id,
            )
        )
    except Exception as exc:
        logger.error("Error in translate_document_task: %s", str(exc))
        raise self.retry(exc=exc)


@celery_app.task(name="ai.analyze_document", bind=True, max_retries=3, default_retry_delay=10)
def analyze_document_task(
    self: Any,
    user_id: str,
    document_id: str,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Background task to perform sentiment & style analysis."""
    try:
        return _run_async(
            _execute_ai_task(
                user_id=user_id,
                document_id=document_id,
                feature_type=AIFeatureType.ANALYZE.value,
                job_id=job_id,
            )
        )
    except Exception as exc:
        logger.error("Error in analyze_document_task: %s", str(exc))
        raise self.retry(exc=exc)


@celery_app.task(name="ai.retry_failed_jobs")
def retry_failed_ai_jobs_task() -> dict[str, Any]:
    """Background cron task to fetch and retry failed/stuck AI jobs."""
    async def _retry_logic() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            job_repo = AIJobRepository(session)
            jobs = await job_repo.get_pending_or_failed_jobs(max_retries=3, limit=10)
            retried_ids = []
            for j in jobs:
                if j.feature_type == AIFeatureType.SUMMARIZE.value:
                    generate_summary_task.delay(str(j.user_id), str(j.document_id), job_id=str(j.id))
                elif j.feature_type == AIFeatureType.CLASSIFY.value:
                    run_classification_task.delay(str(j.user_id), str(j.document_id), job_id=str(j.id))
                elif j.feature_type == AIFeatureType.EXTRACT.value:
                    extract_entities_task.delay(str(j.user_id), str(j.document_id), job_id=str(j.id))
                elif j.feature_type == AIFeatureType.ANALYZE.value:
                    analyze_document_task.delay(str(j.user_id), str(j.document_id), job_id=str(j.id))
                retried_ids.append(str(j.id))
            return {"retried_count": len(retried_ids), "job_ids": retried_ids}

    return _run_async(_retry_logic())
