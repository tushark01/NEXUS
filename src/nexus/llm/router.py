"""Smart model router — picks the best LLM provider for each request."""

from __future__ import annotations

import logging
from typing import AsyncIterator

from nexus.core.errors import LLMError, LLMProviderNotFoundError
from nexus.llm.base import LLMProvider
from nexus.llm.schemas import LLMRequest, LLMResponse, StreamChunk, TaskComplexity

logger = logging.getLogger(__name__)


class ModelRouter:
    """Routes LLM requests to the optimal provider with fallback chains."""

    def __init__(self, default_provider: str) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._default = default_provider
        self._fallback_chains: dict[str, list[str]] = {}
        # Complexity -> provider mapping (configurable)
        self._complexity_routing: dict[TaskComplexity, str | None] = {
            TaskComplexity.SIMPLE: None,  # use default
            TaskComplexity.MEDIUM: None,  # use default
            TaskComplexity.COMPLEX: None,  # use default
        }

    def register_provider(self, provider: LLMProvider) -> None:
        """Register an LLM provider."""
        self._providers[provider.provider_name] = provider
        logger.info("Registered LLM provider: %s", provider.provider_name)

    def add_fallback_chain(self, primary: str, fallbacks: list[str]) -> None:
        """Define a fallback chain for a provider."""
        self._fallback_chains[primary] = fallbacks

    def set_complexity_routing(self, complexity: TaskComplexity, provider: str) -> None:
        """Route a complexity level to a specific provider."""
        self._complexity_routing[complexity] = provider

    def _resolve_provider(self, hint: TaskComplexity = TaskComplexity.MEDIUM) -> str:
        """Determine which provider to use based on complexity hint."""
        routed = self._complexity_routing.get(hint)
        if routed and routed in self._providers:
            return routed
        return self._default

    def _get_provider(self, name: str) -> LLMProvider:
        provider = self._providers.get(name)
        if not provider:
            raise LLMProviderNotFoundError(f"Provider '{name}' not registered")
        return provider

    def _get_chain(self, primary: str) -> list[str]:
        """Get the provider + its fallbacks as an ordered list."""
        chain = [primary]
        chain.extend(self._fallback_chains.get(primary, []))
        return chain

    async def complete(
        self,
        request: LLMRequest,
        hint: TaskComplexity = TaskComplexity.MEDIUM,
    ) -> LLMResponse:
        """Route request to best provider, with fallback on failure."""
        primary = self._resolve_provider(hint)
        chain = self._get_chain(primary)

        last_error: Exception | None = None
        for provider_name in chain:
            if provider_name not in self._providers:
                continue
            provider = self._providers[provider_name]
            try:
                response = await provider.complete(request)
                logger.debug(
                    "LLM complete via %s: %d tokens",
                    provider_name,
                    response.usage.total_tokens,
                )
                return response
            except LLMError as e:
                last_error = e
                logger.warning("Provider %s failed: %s, trying fallback", provider_name, e)

        raise last_error or LLMProviderNotFoundError("No providers available")

    async def stream(
        self,
        request: LLMRequest,
        hint: TaskComplexity = TaskComplexity.MEDIUM,
    ) -> AsyncIterator[StreamChunk]:
        """Stream from the best provider, with fallback on failure."""
        primary = self._resolve_provider(hint)
        chain = self._get_chain(primary)

        last_error: Exception | None = None
        for provider_name in chain:
            if provider_name not in self._providers:
                continue
            provider = self._providers[provider_name]
            try:
                async for chunk in provider.stream(request):
                    yield chunk
                return
            except LLMError as e:
                last_error = e
                logger.warning("Provider %s stream failed: %s, trying fallback", provider_name, e)

        raise last_error or LLMProviderNotFoundError("No providers available")

    @property
    def available_providers(self) -> list[str]:
        return list(self._providers.keys())
