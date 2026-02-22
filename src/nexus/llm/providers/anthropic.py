"""Anthropic (Claude) LLM provider."""

from __future__ import annotations

import logging
from typing import AsyncIterator

import anthropic

from nexus.core.config import LLMProviderConfig
from nexus.core.errors import LLMError, LLMRateLimitError
from nexus.llm.base import LLMProvider
from nexus.llm.schemas import (
    LLMRequest,
    LLMResponse,
    Message,
    StreamChunk,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Claude via the Anthropic SDK."""

    provider_name = "anthropic"

    def __init__(self, config: LLMProviderConfig) -> None:
        if not config.api_key:
            raise LLMError("Anthropic API key is required")
        self.client = anthropic.AsyncAnthropic(
            api_key=config.api_key.get_secret_value()
        )
        self.model = config.model
        self.default_max_tokens = config.max_tokens
        self.default_temperature = config.temperature

    async def complete(self, request: LLMRequest) -> LLMResponse:
        system_msg, messages = self._split_system(request.messages)

        kwargs: dict = {
            "model": request.model or self.model,
            "messages": [self._convert_message(m) for m in messages],
            "max_tokens": request.max_tokens or self.default_max_tokens,
            "temperature": request.temperature if request.temperature is not None else self.default_temperature,
        }
        if system_msg:
            kwargs["system"] = system_msg
        if request.tools:
            kwargs["tools"] = [self._convert_tool(t) for t in request.tools]

        try:
            response = await self.client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except anthropic.APIError as e:
            raise LLMError(f"Anthropic API error: {e}") from e

        return self._to_response(response)

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        system_msg, messages = self._split_system(request.messages)

        kwargs: dict = {
            "model": request.model or self.model,
            "messages": [self._convert_message(m) for m in messages],
            "max_tokens": request.max_tokens or self.default_max_tokens,
            "temperature": request.temperature if request.temperature is not None else self.default_temperature,
        }
        if system_msg:
            kwargs["system"] = system_msg

        try:
            async with self.client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(content=text)
                yield StreamChunk(content="", is_final=True)
        except anthropic.APIError as e:
            raise LLMError(f"Anthropic streaming error: {e}") from e

    def _split_system(self, messages: list[Message]) -> tuple[str | None, list[Message]]:
        """Extract system message (Anthropic uses a separate param)."""
        system = None
        rest = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                rest.append(m)
        return system, rest

    def _convert_message(self, msg: Message) -> dict:
        return {"role": msg.role, "content": msg.content}

    def _convert_tool(self, tool: ToolDefinition) -> dict:
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
        }

    def _to_response(self, response: anthropic.types.Message) -> LLMResponse:
        content = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=block.input)  # type: ignore[arg-type]
                )

        return LLMResponse(
            content=content,
            model=response.model,
            provider=self.provider_name,
            usage=TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            ),
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=response.stop_reason or "stop",
        )
