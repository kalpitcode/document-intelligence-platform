"""
LLM Provider Factory Module
===========================

Factory class `LLMProviderFactory` providing central creation of `LLMProvider` instances.

Architectural Rationale:
- Decouples client code from specific provider implementations.
- Allows seamless configuration switching between OpenAI, Azure OpenAI, Anthropic, Gemini, or Ollama.
"""

from __future__ import annotations

from typing import Any

from app.core.exceptions.base import ValidationException
from app.core.llm.base import LLMProvider
from app.core.llm.openai_provider import OpenAIProvider


class LLMProviderFactory:
    """Factory for instantiating enterprise LLM providers."""

    _providers: dict[str, type[LLMProvider]] = {
        "openai": OpenAIProvider,
        "azure": OpenAIProvider,  # Handled via LiteLLM provider prefix azure/<model>
        "gpt-4o": OpenAIProvider,
        "gpt-4o-mini": OpenAIProvider,
        "gpt-3.5-turbo": OpenAIProvider,
    }

    @classmethod
    def get_provider(
        self,
        provider_name: str = "openai",
        model_name: str = "gpt-4o-mini",
        api_key: str | None = None,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> LLMProvider:
        """
        Instantiate and return an LLMProvider instance.

        Args:
            provider_name: Key identifying provider implementation ("openai", "azure", etc.).
            model_name: Name of target model (e.g., "gpt-4o-mini", "claude-3-5-sonnet").
            api_key: Optional provider API authorization key.
            timeout: Maximum execution timeout in seconds.
            **kwargs: Additional provider parameters.

        Returns:
            Instance of LLMProvider interface.
        """
        key = provider_name.lower().strip()
        provider_cls = self._providers.get(key, OpenAIProvider)

        return provider_cls(
            model_name=model_name,
            api_key=api_key,
            timeout=timeout,
            **kwargs,
        )

    @classmethod
    def register_provider(cls, name: str, provider_cls: type[LLMProvider]) -> None:
        """Register a new LLMProvider implementation at runtime."""
        if not issubclass(provider_cls, LLMProvider):
            raise ValidationException(
                f"Provider class {provider_cls} must inherit from LLMProvider"
            )
        cls._providers[name.lower().strip()] = provider_cls
