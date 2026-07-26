"""
Workflow Automation Schemas Module
===================================

Pydantic V2 data models for workflow templates, execution runs, steps, events, and schedules.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Strict Pydantic V2 validation for input workflow definition DAG structures, retry policies, and condition rules.
- Complete OpenAPI schema documentation and examples.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


class StepConditionSchema(BaseModel):
    """Execution condition schema for a workflow step."""
    model_config = ConfigDict(extra="ignore")

    type: str = Field(
        default="always",
        description="Condition type: 'always', 'on_success', 'on_failure', 'expression'",
    )
    parent_step: str | None = Field(default=None, description="Parent step name to evaluate")
    field: str | None = Field(default=None, description="Field path (e.g. 'steps.ocr.output.page_count')")
    operator: str | None = Field(default="==", description="Comparison operator: '==', '!=', '>', '<', 'contains'")
    value: Any | None = Field(default=None, description="Expected value for expression evaluation")


class StepRetryPolicySchema(BaseModel):
    """Retry policy schema for a workflow step."""
    model_config = ConfigDict(extra="ignore")

    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, ge=0.0, description="Initial retry delay in seconds")
    exponential_backoff: bool = Field(default=True, description="Whether to apply exponential backoff")


class WorkflowStepDefinitionSchema(BaseModel):
    """Single step definition item within a workflow template definition."""
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1, max_length=100, description="Unique step name")
    type: str = Field(..., description="Step type (DOCUMENT_PROCESSING, HYBRID_SEARCH, RAG_QUESTION, SUMMARIZATION, etc.)")
    depends_on: list[str] = Field(default_factory=list, description="List of step names this step depends on")
    condition: StepConditionSchema | None = Field(default=None, description="Optional condition rule for step execution")
    retry_policy: StepRetryPolicySchema | None = Field(default=None, description="Optional retry policy configuration")
    stop_on_failure: bool = Field(default=True, description="Whether workflow run stops if this step fails")
    inputs: dict[str, Any] = Field(default_factory=dict, description="Step input parameters")


class WorkflowDefinitionSchema(BaseModel):
    """Full workflow DAG definition structure."""
    model_config = ConfigDict(extra="ignore")

    steps: list[WorkflowStepDefinitionSchema] = Field(..., min_items=1, description="List of workflow steps")


class CreateWorkflowTemplateRequest(BaseModel):
    """Request payload for creating a new workflow template."""
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1, max_length=255, example="Enterprise Document Processing & RAG Workflow")
    description: str | None = Field(default=None, example="Automated multi-step document intake, OCR, chunking, and AI summarization")
    definition: WorkflowDefinitionSchema = Field(..., description="DAG step definition payload")
    version: int = Field(default=1, ge=1, description="Template version number")


class ExecuteWorkflowRequest(BaseModel):
    """Request payload to trigger execution of a workflow template."""
    model_config = ConfigDict(extra="ignore")

    inputs: dict[str, Any] = Field(default_factory=dict, example={"document_id": "123e4567-e89b-12d3-a456-426614174000"})
    run_async: bool = Field(default=True, description="Execute asynchronously via Celery worker background task")


class CreateWorkflowScheduleRequest(BaseModel):
    """Request payload to add a cron schedule to a workflow template."""
    model_config = ConfigDict(extra="ignore")

    cron_expression: str = Field(..., example="0 0 * * *", description="Standard 5-part cron expression")
    timezone: str = Field(default="UTC", example="UTC", description="Timezone for schedule calculation")
    enabled: bool = Field(default=True, description="Enable automated triggers")


# --- Response Schemas ---

class WorkflowTemplateResponse(BaseModel):
    """Response model for a workflow template."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    version: int
    is_active: bool
    definition_json: dict[str, Any]
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class WorkflowStepResponse(BaseModel):
    """Response model for a single executed workflow step."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_run_id: uuid.UUID
    step_name: str
    step_type: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    retry_count: int
    execution_order: int
    step_metadata: dict[str, Any] | None


class WorkflowEventResponse(BaseModel):
    """Response model for an audit event log."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_run_id: uuid.UUID
    event_type: str
    payload: dict[str, Any] | None
    timestamp: datetime


class WorkflowRunResponse(BaseModel):
    """Response model for a workflow execution run."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    trigger_type: str
    initiated_by: uuid.UUID | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    steps: list[WorkflowStepResponse] = Field(default_factory=list)


class WorkflowScheduleResponse(BaseModel):
    """Response model for a workflow schedule rule."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    cron_expression: str
    timezone: str
    enabled: bool
    next_run: datetime | None
    last_run: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkflowTemplateListResponse(BaseModel):
    """Paginated list response of workflow templates."""
    model_config = ConfigDict(from_attributes=True)

    items: list[WorkflowTemplateResponse] = Field(default_factory=list)
    total: int


class WorkflowRunListResponse(BaseModel):
    """Paginated list response of workflow execution runs."""
    model_config = ConfigDict(from_attributes=True)

    items: list[WorkflowRunResponse] = Field(default_factory=list)
    total: int
