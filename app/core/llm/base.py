"""
LLM Provider Base Module
========================

Defines abstract base contract `LLMProvider` and response container `LLMResponse`.

Architectural Rationale:
- SOLID Principles: Open-Closed Principle (OCP) allows adding Anthropic, Azure OpenAI,
  Gemini, or Ollama providers without modifying business logic.
- Parameter Bounds Validation: Validates temperature (0.0 to 1.0) and max_tokens (1 to 128,000).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.core.exceptions.base import ValidationException


@dataclass(frozen=True)
class LLMResponse:
    """Standardized response dataclass returned by all LLM Providers."""

    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model_name: str
    latency_ms: int
    estimated_cost: float
    raw_response: dict[str, Any] | None = None


class LLMProvider(ABC):
    """
    Abstract Base Class for enterprise LLM providers.

    All model provider implementations (OpenAI, Azure, Anthropic, Gemini, Ollama)
    must subclass this interface.
    """

    def __init__(self, model_name: str, api_key: str | None = None, timeout: float = 30.0) -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.timeout = timeout

    def validate_parameters(self, temperature: float, max_tokens: int) -> None:
        """Validate temperature and max_tokens parameters against safety bounds."""
        if not (0.0 <= temperature <= 1.0):
            raise ValidationException(
                f"Temperature {temperature} is out of bounds [0.0, 1.0]"
            )
        if max_tokens <= 0 or max_tokens > 128000:
            raise ValidationException(
                f"max_tokens {max_tokens} is out of bounds (0, 128000]"
            )

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Asynchronously generate a completion from the LLM provider.

        Args:
            prompt: User/context prompt string.
            system_prompt: Optional system prompt instructions.
            temperature: Sampling temperature (0.0 for deterministic RAG answers).
            max_tokens: Maximum tokens in completion.
            **kwargs: Provider-specific additional parameters.

        Returns:
            LLMResponse object containing text completion and usage telemetry.
        """
        pass
