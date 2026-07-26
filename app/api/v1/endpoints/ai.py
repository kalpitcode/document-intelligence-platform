"""
AI Features API Endpoints Module
================================

FastAPI sub-router presenting production REST endpoints for:
- Summarize document (`POST /api/v1/ai/summarize`)
- Classify document (`POST /api/v1/ai/classify`)
- Extract entities/keywords/action-items (`POST /api/v1/ai/extract`)
- Translate document (`POST /api/v1/ai/translate`)
- Analyze document sentiment & style (`POST /api/v1/ai/analyze`)
- Inspect job status (`GET /api/v1/ai/jobs/{id}`)
- Fetch result payload (`GET /api/v1/ai/results/{id}`)

Architectural Rationale:
- Enforces JWT user authentication and RBAC document authorization.
- Integrates direct APIResponse envelope instantiation.
- Supports synchronous response or asynchronous background Celery worker queuing.
"""

from __future__ import annotations

import logging
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_async_session
from app.dependencies.auth import get_current_active_user
from app.models.user import UserModel
from app.repositories.ai_repository import AIJobRepository, AIResultRepository, FeatureTemplateRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.processing_repository import DocumentChunkRepository
from app.repositories.rag_repository import LLMUsageLogRepository
from app.schemas.ai import (
    AIJobResponse,
    AIResultResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    ClassifyRequest,
    ClassifyResponse,
    ExtractRequest,
    ExtractResponse,
    SummarizeRequest,
    SummarizeResponse,
    TranslateRequest,
    TranslateResponse,
)
from app.schemas.base import APIResponse
from app.services.ai_orchestrator import AIFeatureOrchestrator
from app.services.analysis_service import AnalysisService
from app.services.classification_service import ClassificationService
from app.services.extraction_service import ExtractionService
from app.services.llm_service import LLMService
from app.services.summarization_service import SummarizationService
from app.services.translation_service import TranslationService
from app.workers.tasks.ai_tasks import (
    analyze_document_task,
    extract_entities_task,
    generate_summary_task,
    run_classification_task,
    translate_document_task,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["Enterprise AI Productivity Features"])


async def get_ai_orchestrator(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AIFeatureOrchestrator:
    """Dependency provider constructing AIFeatureOrchestrator with required repositories and services."""
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

    return AIFeatureOrchestrator(
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


@router.post("/summarize", response_model=APIResponse[SummarizeResponse], status_code=status.HTTP_200_OK)
async def summarize_document(
    request: SummarizeRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    orchestrator: Annotated[AIFeatureOrchestrator, Depends(get_ai_orchestrator)],
) -> APIResponse[SummarizeResponse]:
    """Generate short, detailed, executive, or bullet document summary."""
    if request.async_execution:
        job = await orchestrator.job_repo.create_job(
            user_id=current_user.id,
            document_id=request.document_id,
            feature_type="summarize",
        )
        await orchestrator.job_repo.session.commit()

        generate_summary_task.delay(
            user_id=str(current_user.id),
            document_id=str(request.document_id),
            summary_type=request.summary_type.value,
            job_id=str(job.id),
        )

        job_resp = AIJobResponse(
            job_id=job.id,
            document_id=job.document_id,
            feature_type=job.feature_type,
            status=job.status,
            created_at=job.created_at,
        )
        return APIResponse[SummarizeResponse](
            data=SummarizeResponse(job=job_resp, result=None),
            message="Document summarization task queued successfully",
        )

    job, result = await orchestrator.execute_feature(
        user_id=current_user.id,
        document_id=request.document_id,
        feature_type="summarize",
        kwargs={
            "summary_type": request.summary_type.value,
            "include_takeaways": request.include_takeaways,
            "generate_questions": request.generate_questions,
        },
    )

    job_resp = AIJobResponse(
        job_id=job.id,
        document_id=job.document_id,
        feature_type=job.feature_type,
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        latency_ms=job.latency_ms,
        model=job.model,
    )
    result_resp = AIResultResponse(
        result_id=result.id,
        job_id=result.job_id,
        document_id=result.document_id,
        feature_type=result.feature_type,
        result=result.result,
        metadata=result.result_metadata,
        created_at=result.created_at,
    )

    return APIResponse[SummarizeResponse](
        data=SummarizeResponse(job=job_resp, result=result_resp),
        message="Document summary generated successfully",
    )


@router.post("/classify", response_model=APIResponse[ClassifyResponse], status_code=status.HTTP_200_OK)
async def classify_document(
    request: ClassifyRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    orchestrator: Annotated[AIFeatureOrchestrator, Depends(get_ai_orchestrator)],
) -> APIResponse[ClassifyResponse]:
    """Classify document category, topics, and confidence score."""
    if request.async_execution:
        job = await orchestrator.job_repo.create_job(
            user_id=current_user.id,
            document_id=request.document_id,
            feature_type="classify",
        )
        await orchestrator.job_repo.session.commit()

        run_classification_task.delay(
            user_id=str(current_user.id),
            document_id=str(request.document_id),
            job_id=str(job.id),
        )

        job_resp = AIJobResponse(
            job_id=job.id,
            document_id=job.document_id,
            feature_type=job.feature_type,
            status=job.status,
        )
        return APIResponse[ClassifyResponse](
            data=ClassifyResponse(job=job_resp, result=None),
            message="Document classification task queued successfully",
        )

    job, result = await orchestrator.execute_feature(
        user_id=current_user.id,
        document_id=request.document_id,
        feature_type="classify",
    )

    job_resp = AIJobResponse(
        job_id=job.id,
        document_id=job.document_id,
        feature_type=job.feature_type,
        status=job.status,
        latency_ms=job.latency_ms,
        model=job.model,
    )
    result_resp = AIResultResponse(
        result_id=result.id,
        job_id=result.job_id,
        document_id=result.document_id,
        feature_type=result.feature_type,
        result=result.result,
        metadata=result.result_metadata,
        created_at=result.created_at,
    )

    return APIResponse[ClassifyResponse](
        data=ClassifyResponse(job=job_resp, result=result_resp),
        message="Document classification completed successfully",
    )


@router.post("/extract", response_model=APIResponse[ExtractResponse], status_code=status.HTTP_200_OK)
async def extract_information(
    request: ExtractRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    orchestrator: Annotated[AIFeatureOrchestrator, Depends(get_ai_orchestrator)],
) -> APIResponse[ExtractResponse]:
    """Extract keywords, named entities (People, Orgs, Locations, Dates), and action items."""
    if request.async_execution:
        job = await orchestrator.job_repo.create_job(
            user_id=current_user.id,
            document_id=request.document_id,
            feature_type="extract",
        )
        await orchestrator.job_repo.session.commit()

        extract_entities_task.delay(
            user_id=str(current_user.id),
            document_id=str(request.document_id),
            job_id=str(job.id),
        )

        job_resp = AIJobResponse(
            job_id=job.id,
            document_id=job.document_id,
            feature_type=job.feature_type,
            status=job.status,
        )
        return APIResponse[ExtractResponse](
            data=ExtractResponse(job=job_resp, result=None),
            message="Information extraction task queued successfully",
        )

    job, result = await orchestrator.execute_feature(
        user_id=current_user.id,
        document_id=request.document_id,
        feature_type="extract",
        kwargs={
            "extract_entities": request.extract_entities,
            "extract_keywords": request.extract_keywords,
            "extract_action_items": request.extract_action_items,
        },
    )

    job_resp = AIJobResponse(
        job_id=job.id,
        document_id=job.document_id,
        feature_type=job.feature_type,
        status=job.status,
        latency_ms=job.latency_ms,
        model=job.model,
    )
    result_resp = AIResultResponse(
        result_id=result.id,
        job_id=result.job_id,
        document_id=result.document_id,
        feature_type=result.feature_type,
        result=result.result,
        metadata=result.result_metadata,
        created_at=result.created_at,
    )

    return APIResponse[ExtractResponse](
        data=ExtractResponse(job=job_resp, result=result_resp),
        message="Information extracted successfully",
    )


@router.post("/translate", response_model=APIResponse[TranslateResponse], status_code=status.HTTP_200_OK)
async def translate_document(
    request: TranslateRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    orchestrator: Annotated[AIFeatureOrchestrator, Depends(get_ai_orchestrator)],
) -> APIResponse[TranslateResponse]:
    """Translate document into target language."""
    if request.async_execution:
        job = await orchestrator.job_repo.create_job(
            user_id=current_user.id,
            document_id=request.document_id,
            feature_type="translate",
        )
        await orchestrator.job_repo.session.commit()

        translate_document_task.delay(
            user_id=str(current_user.id),
            document_id=str(request.document_id),
            target_language=request.target_language,
            source_language=request.source_language,
            job_id=str(job.id),
        )

        job_resp = AIJobResponse(
            job_id=job.id,
            document_id=job.document_id,
            feature_type=job.feature_type,
            status=job.status,
        )
        return APIResponse[TranslateResponse](
            data=TranslateResponse(job=job_resp, result=None),
            message="Document translation task queued successfully",
        )

    job, result = await orchestrator.execute_feature(
        user_id=current_user.id,
        document_id=request.document_id,
        feature_type="translate",
        kwargs={
            "target_language": request.target_language,
            "source_language": request.source_language,
        },
    )

    job_resp = AIJobResponse(
        job_id=job.id,
        document_id=job.document_id,
        feature_type=job.feature_type,
        status=job.status,
        latency_ms=job.latency_ms,
        model=job.model,
    )
    result_resp = AIResultResponse(
        result_id=result.id,
        job_id=result.job_id,
        document_id=result.document_id,
        feature_type=result.feature_type,
        result=result.result,
        metadata=result.result_metadata,
        created_at=result.created_at,
    )

    return APIResponse[TranslateResponse](
        data=TranslateResponse(job=job_resp, result=result_resp),
        message="Document translated successfully",
    )


@router.post("/analyze", response_model=APIResponse[AnalyzeResponse], status_code=status.HTTP_200_OK)
async def analyze_document(
    request: AnalyzeRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    orchestrator: Annotated[AIFeatureOrchestrator, Depends(get_ai_orchestrator)],
) -> APIResponse[AnalyzeResponse]:
    """Analyze document sentiment, style, readability, and text metrics."""
    if request.async_execution:
        job = await orchestrator.job_repo.create_job(
            user_id=current_user.id,
            document_id=request.document_id,
            feature_type="analyze",
        )
        await orchestrator.job_repo.session.commit()

        analyze_document_task.delay(
            user_id=str(current_user.id),
            document_id=str(request.document_id),
            job_id=str(job.id),
        )

        job_resp = AIJobResponse(
            job_id=job.id,
            document_id=job.document_id,
            feature_type=job.feature_type,
            status=job.status,
        )
        return APIResponse[AnalyzeResponse](
            data=AnalyzeResponse(job=job_resp, result=None),
            message="Document analysis task queued successfully",
        )

    job, result = await orchestrator.execute_feature(
        user_id=current_user.id,
        document_id=request.document_id,
        feature_type="analyze",
    )

    job_resp = AIJobResponse(
        job_id=job.id,
        document_id=job.document_id,
        feature_type=job.feature_type,
        status=job.status,
        latency_ms=job.latency_ms,
        model=job.model,
    )
    result_resp = AIResultResponse(
        result_id=result.id,
        job_id=result.job_id,
        document_id=result.document_id,
        feature_type=result.feature_type,
        result=result.result,
        metadata=result.result_metadata,
        created_at=result.created_at,
    )

    return APIResponse[AnalyzeResponse](
        data=AnalyzeResponse(job=job_resp, result=result_resp),
        message="Document analysis completed successfully",
    )


@router.get("/jobs/{job_id}", response_model=APIResponse[AIJobResponse], status_code=status.HTTP_200_OK)
async def get_job_status(
    job_id: uuid.UUID,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    orchestrator: Annotated[AIFeatureOrchestrator, Depends(get_ai_orchestrator)],
) -> APIResponse[AIJobResponse]:
    """Retrieve execution status for an AI job."""
    job = await orchestrator.job_repo.get_by_id_and_user(job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with ID '{job_id}' not found.")

    job_resp = AIJobResponse(
        job_id=job.id,
        document_id=job.document_id,
        feature_type=job.feature_type,
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        latency_ms=job.latency_ms,
        model=job.model,
        error_message=job.error_message,
        retry_count=job.retry_count,
    )

    return APIResponse[AIJobResponse](
        data=job_resp,
        message="Job status retrieved successfully",
    )


@router.get("/results/{result_id}", response_model=APIResponse[AIResultResponse], status_code=status.HTTP_200_OK)
async def get_result_by_id(
    result_id: uuid.UUID,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    orchestrator: Annotated[AIFeatureOrchestrator, Depends(get_ai_orchestrator)],
) -> APIResponse[AIResultResponse]:
    """Retrieve result payload by result ID."""
    result = await orchestrator.result_repo.get_by_id(result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Result with ID '{result_id}' not found.")

    # Validate permission on underlying document
    has_permission = await orchestrator.document_repo.check_user_permission(result.document_id, current_user.id, "read")
    if not has_permission:
        doc = await orchestrator.document_repo.get_by_id(result.document_id)
        if not doc or doc.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Unauthorized to view result.")

    result_resp = AIResultResponse(
        result_id=result.id,
        job_id=result.job_id,
        document_id=result.document_id,
        feature_type=result.feature_type,
        result=result.result,
        metadata=result.result_metadata,
        created_at=result.created_at,
    )

    return APIResponse[AIResultResponse](
        data=result_resp,
        message="AI Result retrieved successfully",
    )
