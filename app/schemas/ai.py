"""
AI Features API Schemas Module
==============================

Pydantic V2 schemas validating requests and responses for Enterprise AI Feature endpoints:
- Summarize
- Classify
- Extract
- Translate
- Analyze
- Jobs & Results

Architectural Rationale:
- Strict Pydantic V2 field validation.
- OpenAPI example documentation and metadata attributes.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, Field


class SummaryTypeEnum(str, Enum):
    SHORT = "short"
    DETAILED = "detailed"
    EXECUTIVE = "executive"
    BULLET = "bullet"


# ==============================================================================
# Requests
# ==============================================================================

class SummarizeRequest(BaseModel):
    document_id: uuid.UUID = Field(..., description="ID of target document")
    summary_type: SummaryTypeEnum = Field(default=SummaryTypeEnum.EXECUTIVE, description="Type of summary to generate")
    include_takeaways: bool = Field(default=True, description="Extract key takeaways")
    generate_questions: bool = Field(default=True, description="Generate analytical questions")
    async_execution: bool = Field(default=False, description="Run in background as Celery job")


class ClassifyRequest(BaseModel):
    document_id: uuid.UUID = Field(..., description="ID of target document")
    async_execution: bool = Field(default=False, description="Run in background as Celery job")


class ExtractRequest(BaseModel):
    document_id: uuid.UUID = Field(..., description="ID of target document")
    extract_entities: bool = Field(default=True, description="Extract named entities (People, Orgs, Locations, Dates)")
    extract_keywords: bool = Field(default=True, description="Extract key phrases & keywords")
    extract_action_items: bool = Field(default=True, description="Extract action items & deadlines")
    async_execution: bool = Field(default=False, description="Run in background as Celery job")


class TranslateRequest(BaseModel):
    document_id: uuid.UUID = Field(..., description="ID of target document")
    target_language: str = Field(..., min_length=2, description="Target language (e.g. Spanish, French, German, Japanese)")
    source_language: str | None = Field(default=None, description="Optional source language (defaults to auto-detect)")
    async_execution: bool = Field(default=False, description="Run in background as Celery job")


class AnalyzeRequest(BaseModel):
    document_id: uuid.UUID = Field(..., description="ID of target document")
    async_execution: bool = Field(default=False, description="Run in background as Celery job")


# ==============================================================================
# Responses & Envelopes
# ==============================================================================

class AIJobResponse(BaseModel):
    job_id: uuid.UUID = Field(..., description="Unique AI Job UUID")
    document_id: uuid.UUID = Field(..., description="Target document UUID")
    feature_type: str = Field(..., description="Executed feature type")
    status: str = Field(..., description="Current status: pending | processing | completed | failed")
    started_at: datetime | None = Field(default=None, description="Job start timestamp")
    completed_at: datetime | None = Field(default=None, description="Job completion timestamp")
    latency_ms: int = Field(default=0, description="Execution latency in milliseconds")
    model: str | None = Field(default=None, description="LLM model used")
    error_message: str | None = Field(default=None, description="Failure detail if status is failed")
    retry_count: int = Field(default=0, description="Retry attempt count")


class AIResultResponse(BaseModel):
    result_id: uuid.UUID = Field(..., description="Unique AI Result UUID")
    job_id: uuid.UUID | None = Field(default=None, description="Linked job UUID")
    document_id: uuid.UUID = Field(..., description="Target document UUID")
    feature_type: str = Field(..., description="Executed feature type")
    result: dict[str, Any] = Field(..., description="Structured output payload")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Execution metadata")
    created_at: datetime = Field(..., description="Creation timestamp")


class SummarizeResponse(BaseModel):
    job: AIJobResponse
    result: AIResultResponse | None = Field(default=None, description="Result payload if synchronous execution")


class ClassifyResponse(BaseModel):
    job: AIJobResponse
    result: AIResultResponse | None = Field(default=None, description="Result payload if synchronous execution")


class ExtractResponse(BaseModel):
    job: AIJobResponse
    result: AIResultResponse | None = Field(default=None, description="Result payload if synchronous execution")


class TranslateResponse(BaseModel):
    job: AIJobResponse
    result: AIResultResponse | None = Field(default=None, description="Result payload if synchronous execution")


class AnalyzeResponse(BaseModel):
    job: AIJobResponse
    result: AIResultResponse | None = Field(default=None, description="Result payload if synchronous execution")
