"""
Unit Tests for Workflow Engine & Scheduler
=========================================

Tests DAG topological sorting, validation rules, circular dependency checks,
condition expression evaluation, and retry backoff delays.
"""

from __future__ import annotations

from unittest.mock import MagicMock

pytest_plugins = ["pytest_asyncio"]

import pytest

from app.repositories.workflow_repository import WorkflowRepository
from app.services.workflow_engine import (
    WorkflowEngine,
    WorkflowValidationError,
)
from app.services.workflow_scheduler_service import WorkflowSchedulerService


@pytest.fixture
def mock_workflow_repo() -> MagicMock:
    return MagicMock(spec=WorkflowRepository)


@pytest.fixture
def workflow_engine(mock_workflow_repo: MagicMock) -> WorkflowEngine:
    return WorkflowEngine(mock_workflow_repo)


def test_validate_valid_dag_definition(workflow_engine: WorkflowEngine) -> None:
    valid_def = {
        "steps": [
            {"name": "ocr", "type": "DOCUMENT_PROCESSING"},
            {"name": "summarize", "type": "SUMMARIZATION", "depends_on": ["ocr"]},
            {"name": "notify", "type": "NOTIFICATION_STUB", "depends_on": ["summarize"]},
        ]
    }
    validated = workflow_engine.validate_definition(valid_def)
    assert validated == valid_def


def test_topological_sort_order(workflow_engine: WorkflowEngine) -> None:
    valid_def = {
        "steps": [
            {"name": "notify", "type": "NOTIFICATION_STUB", "depends_on": ["summarize"]},
            {"name": "summarize", "type": "SUMMARIZATION", "depends_on": ["ocr"]},
            {"name": "ocr", "type": "DOCUMENT_PROCESSING"},
        ]
    }
    ordered = workflow_engine.get_topological_execution_order(valid_def)
    names = [s["name"] for s in ordered]
    assert names == ["ocr", "summarize", "notify"]


def test_circular_dependency_detection(workflow_engine: WorkflowEngine) -> None:
    circular_def = {
        "steps": [
            {"name": "step_a", "type": "HYBRID_SEARCH", "depends_on": ["step_b"]},
            {"name": "step_b", "type": "RAG_QUESTION", "depends_on": ["step_a"]},
        ]
    }
    with pytest.raises(WorkflowValidationError, match="Circular dependency detected"):
        workflow_engine.validate_definition(circular_def)


def test_unsupported_step_type(workflow_engine: WorkflowEngine) -> None:
    invalid_type_def = {
        "steps": [
            {"name": "invalid_step", "type": "UNSUPPORTED_TYPE"}
        ]
    }
    with pytest.raises(WorkflowValidationError, match="Unsupported step type"):
        workflow_engine.validate_definition(invalid_type_def)


def test_condition_evaluation_expression(workflow_engine: WorkflowEngine) -> None:
    condition = {
        "type": "expression",
        "field": "steps.ocr.output.page_count",
        "operator": ">",
        "value": 5,
    }
    previous_outputs = {
        "ocr": {"status": "COMPLETED", "output": {"page_count": 10}}
    }
    result = workflow_engine.evaluate_condition(condition, previous_outputs, {})
    assert result is True

    condition_false = {
        "type": "expression",
        "field": "steps.ocr.output.page_count",
        "operator": ">",
        "value": 15,
    }
    result_false = workflow_engine.evaluate_condition(condition_false, previous_outputs, {})
    assert result_false is False


def test_retry_backoff_calculation(workflow_engine: WorkflowEngine) -> None:
    delay_1 = workflow_engine.calculate_retry_delay(attempt=1, max_retries=3, base_delay_sec=2.0, exponential_backoff=True)
    delay_2 = workflow_engine.calculate_retry_delay(attempt=2, max_retries=3, base_delay_sec=2.0, exponential_backoff=True)
    delay_3 = workflow_engine.calculate_retry_delay(attempt=3, max_retries=3, base_delay_sec=2.0, exponential_backoff=True)

    assert delay_1 == 2.0
    assert delay_2 == 4.0
    assert delay_3 == 8.0


def test_scheduler_next_run_calculation(mock_workflow_repo: MagicMock) -> None:
    scheduler = WorkflowSchedulerService(mock_workflow_repo)
    next_run = scheduler.calculate_next_run("0 0 * * *")
    assert next_run is not None
