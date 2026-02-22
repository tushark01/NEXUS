"""LLM provider protocol — the interface all providers must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from nexus.llm.schemas import LLMRequest, LLMResponse, StreamChunk


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    provider_name: str

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a completion request and return the full response."""

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        """Stream a completion response chunk by chunk."""

    def supports_tools(self) -> bool:
        """Whether this provider supports tool/function calling."""
        return True

    def max_context_window(self) -> int:
        """Maximum context window size in tokens."""
        return 128_000
