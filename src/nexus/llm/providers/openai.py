"""OpenAI (GPT) LLM provider."""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import openai

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


class OpenAIProvider(LLMProvider):
    """GPT via the OpenAI SDK."""

    provider_name = "openai"

    def __init__(self, config: LLMProviderConfig) -> None:
        if not config.api_key:
            raise LLMError("OpenAI API key is required")
        self.client = openai.AsyncOpenAI(
            api_key=config.api_key.get_secret_value(),
            base_url=config.base_url,
        )
        self.model = config.model
        self.default_max_tokens = config.max_tokens
        self.default_temperature = config.temperature

    async def complete(self, request: LLMRequest) -> LLMResponse:
        kwargs: dict = {
            "model": request.model or self.model,
            "messages": [self._convert_message(m) for m in request.messages],
            "max_tokens": request.max_tokens or self.default_max_tokens,
            "temperature": request.temperature if request.temperature is not None else self.default_temperature,
        }
        if request.tools:
            kwargs["tools"] = [self._convert_tool(t) for t in request.tools]

        try:
            response = await self.client.chat.completions.create(**kwargs)
        except openai.RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except openai.APIError as e:
            raise LLMError(f"OpenAI API error: {e}") from e

        return self._to_response(response)

    async def stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        kwargs: dict = {
            "model": request.model or self.model,
            "messages": [self._convert_message(m) for m in request.messages],
            "max_tokens": request.max_tokens or self.default_max_tokens,
            "temperature": request.temperature if request.temperature is not None else self.default_temperature,
            "stream": True,
        }

        try:
            response = await self.client.chat.completions.create(**kwargs)
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield StreamChunk(content=delta.content)
            yield StreamChunk(content="", is_final=True)
        except openai.APIError as e:
            raise LLMError(f"OpenAI streaming error: {e}") from e

    def _convert_message(self, msg: Message) -> dict:
        result: dict = {"role": msg.role, "content": msg.content}
        if msg.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in msg.tool_calls
            ]
        if msg.tool_call_id:
            result["tool_call_id"] = msg.tool_call_id
        return result

    def _convert_tool(self, tool: ToolDefinition) -> dict:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    def _to_response(self, response: openai.types.chat.ChatCompletion) -> LLMResponse:
        choice = response.choices[0]
        content = choice.message.content or ""

        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments) if tc.function.arguments else {},
                )
                for tc in choice.message.tool_calls
            ]

        usage = TokenUsage()
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        return LLMResponse(
            content=content,
            model=response.model,
            provider=self.provider_name,
            usage=usage,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
        )
