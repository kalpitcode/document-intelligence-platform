"""
Workflow Engine API Endpoints Module
====================================

FastAPI sub-router presenting production REST endpoints for:
- Create Workflow Template (`POST /api/v1/workflows`)
- Execute Workflow (`POST /api/v1/workflows/{id}/execute`)
- Cancel Workflow Run (`POST /api/v1/workflows/{id}/cancel`)
- List Workflow Templates (`GET /api/v1/workflows`)
- Get Workflow Template (`GET /api/v1/workflows/{id}`)
- List Workflow Runs (`GET /api/v1/workflows/{id}/runs`)
- Get Workflow Run Detail (`GET /api/v1/workflows/runs/{run_id}`)

**Architectural Rationale:**
- Clean Architecture API layer enforcing JWT authentication and user RBAC.
- Formats standard `APIResponse` envelopes for all return values.
- Leverages Celery tasks for asynchronous execution.
"""

from __future__ import annotations

import logging
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_async_session
from app.dependencies.auth import get_current_active_user
from app.models.user import UserModel
from app.repositories.workflow_repository import WorkflowRepository
from app.schemas.base import APIResponse
from app.schemas.workflow import (
    CreateWorkflowTemplateRequest,
    ExecuteWorkflowRequest,
    WorkflowRunListResponse,
    WorkflowRunResponse,
    WorkflowTemplateListResponse,
    WorkflowTemplateResponse,
)
from app.services.workflow_engine import WorkflowEngine, WorkflowValidationError
from app.workers.tasks.workflow_tasks import execute_workflow_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflow Automation Engine"])


@router.post(
    "",
    response_model=APIResponse[WorkflowTemplateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Workflow Template",
    description="Create a new versioned multi-step workflow template definition with step DAG rules, conditions, and retry policies.",
)
async def create_workflow_template(
    payload: CreateWorkflowTemplateRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> APIResponse[WorkflowTemplateResponse]:
    """Create a new workflow template."""
    repo = WorkflowRepository(session)
    engine = WorkflowEngine(repo)

    try:
        def_dict = payload.definition.model_dump()
        engine.validate_definition(def_dict)
    except WorkflowValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow definition: {str(err)}",
        )

    template = await repo.create_template(
        name=payload.name,
        description=payload.description,
        version=payload.version,
        definition_json=def_dict,
        owner_id=current_user.id,
    )
    await session.commit()

    return APIResponse(
        data=WorkflowTemplateResponse.model_validate(template),
        message="Workflow template created successfully",
    )


@router.get(
    "",
    response_model=APIResponse[WorkflowTemplateListResponse],
    summary="List Workflow Templates",
    description="List active workflow templates with pagination.",
)
async def list_workflow_templates(
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_active: bool | None = Query(None),
) -> APIResponse[WorkflowTemplateListResponse]:
    """List available workflow templates."""
    repo = WorkflowRepository(session)
    templates, total = await repo.list_templates(
        owner_id=None if getattr(current_user, "is_superuser", False) else current_user.id,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )

    items = [WorkflowTemplateResponse.model_validate(t) for t in templates]
    return APIResponse(
        data=WorkflowTemplateListResponse(items=items, total=total),
        message="Workflow templates retrieved successfully",
    )


@router.get(
    "/{id}",
    response_model=APIResponse[WorkflowTemplateResponse],
    summary="Get Workflow Template Detail",
    description="Fetch a specific workflow template by ID.",
)
async def get_workflow_template(
    id: uuid.UUID,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> APIResponse[WorkflowTemplateResponse]:
    """Get workflow template detail by ID."""
    repo = WorkflowRepository(session)
    template = await repo.get_template_by_id(id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow template '{id}' not found",
        )

    return APIResponse(
        data=WorkflowTemplateResponse.model_validate(template),
        message="Workflow template retrieved successfully",
    )


@router.post(
    "/{id}/execute",
    response_model=APIResponse[WorkflowRunResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute Workflow Template",
    description="Trigger execution of a workflow template asynchronously or synchronously.",
)
async def execute_workflow(
    id: uuid.UUID,
    payload: ExecuteWorkflowRequest,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> APIResponse[WorkflowRunResponse]:
    """Trigger workflow execution."""
    repo = WorkflowRepository(session)
    template = await repo.get_template_by_id(id)
    if not template or not template.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active workflow template '{id}' not found",
        )

    # Create run execution record
    run = await repo.create_run(
        workflow_id=template.id,
        trigger_type="MANUAL",
        initiated_by=current_user.id,
    )
    await session.commit()

    if payload.run_async:
        # Enqueue background Celery task execution
        execute_workflow_task.delay(str(run.id), payload.inputs)
    else:
        # Synchronous execution
        from app.core.storage.minio_provider import MinIOStorageProvider
        from app.core.vector.qdrant_provider import QdrantProvider
        from app.repositories.ai_repository import AIJobRepository, AIResultRepository, FeatureTemplateRepository
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
        from app.services.prompt_builder_service import PromptBuilderService
        from app.services.rag_service import RAGService
        from app.services.reranking_service import RerankingService
        from app.services.storage_service import StorageService
        from app.services.summarization_service import SummarizationService
        from app.services.translation_service import TranslationService
        from app.services.vector_service import VectorService
        from app.services.workflow_orchestrator import WorkflowOrchestrator

        engine = WorkflowEngine(repo)
        doc_repo = DocumentRepository(session)
        chunk_repo = DocumentChunkRepository(session)
        doc_proc = DocumentProcessingService(
            document_repo=doc_repo,
            content_repo=DocumentContentRepository(session),
            chunk_repo=chunk_repo,
            job_repo=ProcessingJobRepository(session),
            table_repo=ExtractedTableRepository(session),
            image_repo=ExtractedImageRepository(session),
            storage_service=StorageService(MinIOStorageProvider()),
        )
        emb = EmbeddingService()
        vec_service = VectorService(QdrantProvider())
        search = HybridSearchService(
            vector_service=vec_service,
            embedding_service=emb,
        )
        knowledge_svc = KnowledgeOrchestrationService(
            embedding_job_repo=EmbeddingJobRepository(session),
            search_history_repo=SearchHistoryRepository(session),
            embedding_model_repo=EmbeddingModelRepository(session),
            chunk_repo=chunk_repo,
            doc_repo=doc_repo,
            embedding_service=emb,
            vector_service=vec_service,
            hybrid_search_service=search,
            reranking_service=RerankingService(),
        )
        ctx = ContextRetrievalService(knowledge_svc)
        llm = LLMService()
        rag = RAGService(
            context_retrieval_service=ctx,
            prompt_builder_service=PromptBuilderService(),
            llm_service=llm,
            session_repo=ChatSessionRepository(session),
            message_repo=ChatMessageRepository(session),
            usage_log_repo=LLMUsageLogRepository(session),
        )
        ai_orch = AIFeatureOrchestrator(
            document_repo=DocumentRepository(session),
            chunk_repo=DocumentChunkRepository(session),
            job_repo=AIJobRepository(session),
            result_repo=AIResultRepository(session),
            template_repo=FeatureTemplateRepository(session),
            usage_log_repo=LLMUsageLogRepository(session),
            summarization_service=SummarizationService(llm),
            classification_service=ClassificationService(llm),
            extraction_service=ExtractionService(llm),
            translation_service=TranslationService(llm),
            analysis_service=AnalysisService(llm),
        )
        orch = WorkflowOrchestrator(repo, engine, doc_proc, emb, search, rag, ai_orch)
        run = await orch.execute_run(run.id, initial_input=payload.inputs)
        await session.commit()

    run_detail = await repo.get_run_by_id(run.id, include_steps=True)
    assert run_detail is not None

    return APIResponse(
        data=WorkflowRunResponse.model_validate(run_detail),
        message="Workflow execution initiated",
    )


@router.post(
    "/{id}/cancel",
    response_model=APIResponse[WorkflowRunResponse],
    summary="Cancel Active Workflow Run",
    description="Cancel an in-progress or queued workflow execution run.",
)
async def cancel_workflow_run(
    id: uuid.UUID,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> APIResponse[WorkflowRunResponse]:
    """Cancel a workflow execution run."""
    repo = WorkflowRepository(session)
    run = await repo.get_run_by_id(id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{id}' not found",
        )

    updated_run = await repo.update_run(run_id=run.id, status="CANCELLED")
    await repo.create_event(workflow_run_id=run.id, event_type="WorkflowCancelled", payload={"cancelled_by": str(current_user.id)})
    await session.commit()

    assert updated_run is not None
    return APIResponse(
        data=WorkflowRunResponse.model_validate(updated_run),
        message="Workflow run cancelled successfully",
    )


@router.get(
    "/{id}/runs",
    response_model=APIResponse[WorkflowRunListResponse],
    summary="List Workflow Runs for Template",
    description="Fetch execution history runs for a specific workflow template.",
)
async def list_template_workflow_runs(
    id: uuid.UUID,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
) -> APIResponse[WorkflowRunListResponse]:
    """List runs for a workflow template."""
    repo = WorkflowRepository(session)
    runs, total = await repo.list_runs(
        workflow_id=id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )

    items = [WorkflowRunResponse.model_validate(r) for r in runs]
    return APIResponse(
        data=WorkflowRunListResponse(items=items, total=total),
        message="Workflow runs retrieved successfully",
    )


@router.get(
    "/runs/{run_id}",
    response_model=APIResponse[WorkflowRunResponse],
    summary="Get Workflow Run Detail",
    description="Fetch full execution detail, steps, and telemetry for a workflow run.",
)
async def get_workflow_run_detail(
    run_id: uuid.UUID,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> APIResponse[WorkflowRunResponse]:
    """Get workflow run detail by run ID."""
    repo = WorkflowRepository(session)
    run = await repo.get_run_by_id(run_id, include_steps=True, include_events=True)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow run '{run_id}' not found",
        )

    return APIResponse(
        data=WorkflowRunResponse.model_validate(run),
        message="Workflow run detail retrieved successfully",
    )
