"""
Workflow Engine Module
======================

Core execution engine responsible for loading, validating, DAG topological sorting,
condition evaluation, retry policies, state tracking, and audit event publishing.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles (Single Responsibility for workflow execution).
- Validates DAG structures and detects circular dependencies prior to execution.
- Evaluates step runtime conditions (Success, Failure, Boolean expression, Document Metadata, Previous Step Outputs).
- Enforces configurable retry policies (Max retries, exponential backoff, retry delay).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
import math
import re
from typing import Any
import uuid

from app.models.workflow import (
    WorkflowRunModel,
    WorkflowStepModel,
    WorkflowTemplateModel,
)
from app.repositories.workflow_repository import WorkflowRepository

logger = logging.getLogger(__name__)


class WorkflowValidationError(Exception):
    """Raised when a workflow definition JSON is invalid or contains circular dependencies."""
    pass


class WorkflowExecutionError(Exception):
    """Raised when workflow execution encounters an unhandled fatal error."""
    pass


SUPPORTED_STEP_TYPES = {
    "DOCUMENT_PROCESSING",
    "EMBEDDING_GENERATION",
    "HYBRID_SEARCH",
    "RAG_QUESTION",
    "SUMMARIZATION",
    "CLASSIFICATION",
    "EXTRACTION",
    "TRANSLATION",
    "ANALYSIS",
    "APPROVAL",
    "NOTIFICATION_STUB",
}


class WorkflowEngine:
    """Core Workflow Execution Engine."""

    def __init__(self, workflow_repo: WorkflowRepository) -> None:
        self.repo = workflow_repo

    # --- Workflow Definition Validation ---

    def validate_definition(self, definition_json: dict[str, Any]) -> dict[str, Any]:
        """
        Validate workflow definition JSON schema, step types, dependencies, and circular dependency prevention.
        """
        if not isinstance(definition_json, dict):
            raise WorkflowValidationError("Workflow definition must be a JSON dictionary object.")

        steps = definition_json.get("steps")
        if not steps or not isinstance(steps, list):
            raise WorkflowValidationError("Workflow definition must contain a non-empty 'steps' list.")

        step_names: set[str] = set()
        graph: dict[str, set[str]] = {}

        for step in steps:
            if not isinstance(step, dict):
                raise WorkflowValidationError("Each step entry must be a dictionary.")
            
            name = step.get("name")
            if not name or not isinstance(name, str):
                raise WorkflowValidationError("Step missing valid 'name' string property.")
            
            if name in step_names:
                raise WorkflowValidationError(f"Duplicate step name '{name}' found in workflow definition.")
            step_names.add(name)

            step_type = step.get("type", "").upper()
            if step_type not in SUPPORTED_STEP_TYPES:
                raise WorkflowValidationError(
                    f"Unsupported step type '{step_type}' in step '{name}'. Supported: {sorted(list(SUPPORTED_STEP_TYPES))}"
                )

            deps = step.get("depends_on", [])
            if not isinstance(deps, list):
                raise WorkflowValidationError(f"Step '{name}' 'depends_on' must be a list of step names.")
            
            graph[name] = set(deps)

        # Check that all declared dependencies exist
        for step_name, deps in graph.items():
            for dep in deps:
                if dep not in step_names:
                    raise WorkflowValidationError(f"Step '{step_name}' depends on unknown step '{dep}'.")

        # Detect Circular Dependencies (Kahn's Algorithm / Cycle detection)
        in_degree = {name: 0 for name in step_names}
        adjacency: dict[str, list[str]] = {name: [] for name in step_names}

        for node, deps in graph.items():
            for dep in deps:
                adjacency[dep].append(node)
                in_degree[node] += 1

        queue = [node for node in step_names if in_degree[node] == 0]
        visited_count = 0

        while queue:
            node = queue.pop(0)
            visited_count += 1
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(step_names):
            raise WorkflowValidationError("Circular dependency detected in workflow definition DAG.")

        return definition_json

    def get_topological_execution_order(self, definition_json: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Return steps sorted in topological DAG execution order.
        """
        steps = definition_json.get("steps", [])
        step_dict = {s["name"]: s for s in steps}
        graph = {s["name"]: set(s.get("depends_on", [])) for s in steps}

        in_degree = {name: 0 for name in step_dict}
        adjacency: dict[str, list[str]] = {name: [] for name in step_dict}

        for node, deps in graph.items():
            for dep in deps:
                adjacency[dep].append(node)
                in_degree[node] += 1

        queue = [name for name in step_dict if in_degree[name] == 0]
        ordered_steps = []

        while queue:
            node = queue.pop(0)
            ordered_steps.append(step_dict[node])
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return ordered_steps

    # --- Condition Evaluation ---

    def evaluate_condition(
        self,
        condition: dict[str, Any] | None,
        previous_outputs: dict[str, Any],
        context_metadata: dict[str, Any],
    ) -> bool:
        """
        Evaluate conditional execution rules:
        - Success / Failure checks on parent step status
        - Boolean condition expression on previous step outputs or metadata
        """
        if not condition:
            return True

        cond_type = condition.get("type", "always").lower()

        if cond_type == "always":
            return True

        if cond_type == "on_success":
            parent_step = condition.get("parent_step")
            if not parent_step:
                return True
            parent_state = previous_outputs.get(parent_step, {})
            return parent_state.get("status") == "COMPLETED"

        if cond_type == "on_failure":
            parent_step = condition.get("parent_step")
            if not parent_step:
                return False
            parent_state = previous_outputs.get(parent_step, {})
            return parent_state.get("status") == "FAILED"

        if cond_type == "expression":
            field = condition.get("field")
            operator = condition.get("operator", "==")
            expected_val = condition.get("value")

            if not field:
                return True

            # Resolve field value from previous outputs or context metadata
            actual_val = self._resolve_path(field, previous_outputs, context_metadata)

            if operator in ("==", "eq"):
                return actual_val == expected_val
            elif operator in ("!=", "neq"):
                return actual_val != expected_val
            elif operator in (">", "gt"):
                return float(actual_val or 0) > float(expected_val or 0)
            elif operator in ("<", "lt"):
                return float(actual_val or 0) < float(expected_val or 0)
            elif operator == "contains":
                return expected_val in (actual_val or "")
            elif operator == "is_not_none":
                return actual_val is not None

        return True

    def _resolve_path(
        self,
        path: str,
        previous_outputs: dict[str, Any],
        context_metadata: dict[str, Any],
    ) -> Any:
        """Resolve nested property path e.g. 'steps.ocr.output.page_count' or 'metadata.mime_type'."""
        data = {
            "steps": previous_outputs,
            "metadata": context_metadata,
        }
        parts = path.split(".")
        curr: Any = data
        for p in parts:
            if isinstance(curr, dict) and p in curr:
                curr = curr[p]
            else:
                return None
        return curr

    # --- Retry Policy Helper ---

    def calculate_retry_delay(
        self,
        attempt: int,
        max_retries: int = 3,
        base_delay_sec: float = 1.0,
        exponential_backoff: bool = True,
    ) -> float:
        """Calculate retry delay with optional exponential backoff."""
        if attempt > max_retries:
            return 0.0
        if exponential_backoff:
            return base_delay_sec * math.pow(2, max(0, attempt - 1))
        return base_delay_sec
