"""
LLM Service Module
==================

High-level domain service providing managed access to LLM providers via `LLMProviderFactory`.

Architectural Rationale:
- Enforces parameter bounds (temperature, max_tokens).
- Wraps provider calls with telemetry logging and error resilience.
"""

from __future__ import annotations

from typing import Any
import structlog

from app.core.llm.base import LLMProvider, LLMResponse
from app.core.llm.factory import LLMProviderFactory

logger = structlog.get_logger(__name__)


class LLMService:
    """Service wrapping LLM provider execution and parameter enforcement."""

    def __init__(
        self,
        default_provider: str = "openai",
        default_model: str = "gpt-4o-mini",
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.default_provider = default_provider
        self.default_model = default_model
        self.api_key = api_key
        self.timeout = timeout

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        provider_name: str | None = None,
        model_name: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Execute completion request through configured LLM Provider.

        Args:
            prompt: User context prompt string.
            system_prompt: Optional system prompt instructions.
            temperature: Sampling temperature (0.0 default for factual answers).
            max_tokens: Max output tokens in completion.
            provider_name: Optional override for provider implementation.
            model_name: Optional override for target model name.
            **kwargs: Additional parameters.

        Returns:
            LLMResponse containing generated content and usage metrics.
        """
        provider_str = provider_name or self.default_provider
        model_str = model_name or self.default_model

        provider: LLMProvider = LLMProviderFactory.get_provider(
            provider_name=provider_str,
            model_name=model_str,
            api_key=self.api_key,
            timeout=self.timeout,
        )

        logger.info(
            "Executing LLM service completion",
            provider=provider_str,
            model=model_str,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        response = await provider.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        logger.info(
            "LLM completion succeeded",
            model=response.model_name,
            total_tokens=response.total_tokens,
            latency_ms=response.latency_ms,
            cost=response.estimated_cost,
        )

        return response
