"""
AI Feature Orchestrator Module
==============================

Master orchestrator managing user authorization, document context retrieval, AI feature execution,
job status tracking, and structured result persistence.

Architectural Rationale:
- Clean Architecture & SOLID design principles.
- Single Responsibility: Coordinates workflow between RBAC authorization, document data layer, AI feature services, and repository storage.
"""

from __future__ import annotations

import time
from typing import Any
import uuid

import structlog

from app.core.exceptions.base import AuthorizationException, NotFoundError, ProcessingError
from app.models.ai import AIFeatureType, AIJobModel, AIJobStatus, AIResultModel
from app.repositories.ai_repository import AIJobRepository, AIResultRepository, FeatureTemplateRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.processing_repository import DocumentChunkRepository
from app.repositories.rag_repository import LLMUsageLogRepository
from app.services.analysis_service import AnalysisService
from app.services.classification_service import ClassificationService
from app.services.extraction_service import ExtractionService
from app.services.summarization_service import SummarizationService
from app.services.translation_service import TranslationService

logger = structlog.get_logger(__name__)


class AIFeatureOrchestrator:
    """Master Orchestrator for Enterprise AI Productivity Features."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        chunk_repo: DocumentChunkRepository,
        job_repo: AIJobRepository,
        result_repo: AIResultRepository,
        template_repo: FeatureTemplateRepository,
        usage_log_repo: LLMUsageLogRepository,
        summarization_service: SummarizationService,
        classification_service: ClassificationService,
        extraction_service: ExtractionService,
        translation_service: TranslationService,
        analysis_service: AnalysisService,
    ) -> None:
        self.document_repo = document_repo
        self.chunk_repo = chunk_repo
        self.job_repo = job_repo
        self.result_repo = result_repo
        self.template_repo = template_repo
        self.usage_log_repo = usage_log_repo
        self.summarization_service = summarization_service
        self.classification_service = classification_service
        self.extraction_service = extraction_service
        self.translation_service = translation_service
        self.analysis_service = analysis_service

    async def execute_feature(
        self,
        user_id: uuid.UUID | str,
        document_id: uuid.UUID | str,
        feature_type: str | AIFeatureType,
        kwargs: dict[str, Any] | None = None,
        job_id: uuid.UUID | str | None = None,
    ) -> tuple[AIJobModel, AIResultModel]:
        """
        Execute an AI feature end-to-end:
        1. Validate document access (RBAC).
        2. Retrieve document content text.
        3. Track/Update AIJob status.
        4. Execute requested AI Feature Service.
        5. Persist AIResultModel & LLM usage log.
        """
        u_id = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        d_id = uuid.UUID(str(document_id)) if isinstance(document_id, str) else document_id
        feat_str = feature_type.value if isinstance(feature_type, AIFeatureType) else str(feature_type)
        extra_args = kwargs or {}

        start_time = time.perf_counter()

        # 1. Permission Validation (RBAC)
        doc = await self.document_repo.get_by_id(d_id)
        if not doc:
            raise NotFoundError(f"Document with ID '{d_id}' not found.")

        # Owner or explicit RBAC authorization check
        if doc.owner_id != u_id:
            has_permission = await self.document_repo.check_user_permission(d_id, u_id, "read")
            if not has_permission:
                raise AuthorizationException("Access denied: You do not have permission to access this document.")

        # 2. Retrieve Document Content Text
        chunks, _ = await self.chunk_repo.get_chunks_by_document_id(d_id, limit=1000)
        if not chunks:
            raise ProcessingError(f"No processed content available for document '{d_id}'. Ensure document is processed.")

        full_text = "\n\n".join(c.content for c in chunks if c.content)
        if not full_text.strip():
            raise ProcessingError(f"Document '{d_id}' content is empty.")

        # 3. Create or Fetch Job
        if job_id:
            j_id = uuid.UUID(str(job_id)) if isinstance(job_id, str) else job_id
            job = await self.job_repo.get_by_id(j_id)
            if not job:
                job = await self.job_repo.create_job(u_id, d_id, feat_str)
        else:
            job = await self.job_repo.create_job(u_id, d_id, feat_str)

        await self.job_repo.update_status(job, AIJobStatus.PROCESSING)

        try:
            # 4. Feature Routing
            if feat_str == AIFeatureType.SUMMARIZE.value:
                res_dict = await self.summarization_service.generate_summary(
                    text_content=full_text,
                    summary_type=extra_args.get("summary_type", "executive"),
                    include_takeaways=extra_args.get("include_takeaways", True),
                    generate_questions=extra_args.get("generate_questions", True),
                )
            elif feat_str == AIFeatureType.CLASSIFY.value:
                res_dict = await self.classification_service.classify_document(full_text)
            elif feat_str == AIFeatureType.EXTRACT.value:
                res_dict = await self.extraction_service.extract_information(
                    text_content=full_text,
                    extract_entities=extra_args.get("extract_entities", True),
                    extract_keywords=extra_args.get("extract_keywords", True),
                    extract_action_items=extra_args.get("extract_action_items", True),
                )
            elif feat_str == AIFeatureType.TRANSLATE.value:
                target_lang = extra_args.get("target_language", "English")
                source_lang = extra_args.get("source_language")
                res_dict = await self.translation_service.translate_document(
                    text_content=full_text,
                    target_language=target_lang,
                    source_language=source_lang,
                )
            elif feat_str == AIFeatureType.ANALYZE.value:
                res_dict = await self.analysis_service.analyze_document(full_text)
            else:
                raise ProcessingError(f"Unsupported AI feature type: '{feat_str}'")

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            model_used = res_dict.pop("model_used", "unknown-model")
            p_tokens = res_dict.pop("prompt_tokens", 0)
            c_tokens = res_dict.pop("completion_tokens", 0)
            t_tokens = res_dict.pop("total_tokens", 0)

            # 5. Persist AIResult & Complete Job
            result = await self.result_repo.create_result(
                document_id=d_id,
                feature_type=feat_str,
                result=res_dict,
                metadata={
                    "model": model_used,
                    "prompt_tokens": p_tokens,
                    "completion_tokens": c_tokens,
                    "total_tokens": t_tokens,
                    "latency_ms": latency_ms,
                },
                job_id=job.id,
            )

            job = await self.job_repo.update_status(
                job=job,
                status=AIJobStatus.COMPLETED,
                latency_ms=latency_ms,
                model=model_used,
            )

            # 6. Audit Usage Log
            await self.usage_log_repo.log_usage(
                user_id=u_id,
                model=model_used,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=t_tokens,
                cost=0.0,
                latency_ms=latency_ms,
                prompt_template_name=f"ai_feature_{feat_str}",
                prompt_version="1.0.0",
            )

            # Commit transaction
            await self.job_repo.session.commit()

            logger.info(
                "AI feature executed successfully",
                feature_type=feat_str,
                document_id=str(d_id),
                job_id=str(job.id),
                latency_ms=latency_ms,
            )

            return job, result

        except Exception as exc:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            job = await self.job_repo.update_status(
                job=job,
                status=AIJobStatus.FAILED,
                error_message=str(exc),
                latency_ms=latency_ms,
            )
            await self.job_repo.session.commit()
            logger.error("AI feature execution failed: %s", str(exc), exc_info=True)
            raise
