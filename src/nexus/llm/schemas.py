"""LLM request/response schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single message in a conversation."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class ToolCall(BaseModel):
    """An LLM-initiated tool/function call."""

    id: str
    name: str
    arguments: dict[str, Any] = {}


class ToolDefinition(BaseModel):
    """Schema for a tool the LLM can call."""

    name: str
    description: str
    parameters: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )


class TokenUsage(BaseModel):
    """Token usage for a single LLM request."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float | None = None


class LLMRequest(BaseModel):
    """Request to an LLM provider."""

    messages: list[Message]
    model: str | None = None  # override provider default
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[ToolDefinition] | None = None
    stream: bool = False


class LLMResponse(BaseModel):
    """Response from an LLM provider."""

    content: str
    model: str
    provider: str
    usage: TokenUsage = TokenUsage()
    tool_calls: list[ToolCall] | None = None
    finish_reason: str = "stop"


class StreamChunk(BaseModel):
    """A single chunk from a streaming LLM response."""

    content: str = ""
    is_final: bool = False


class TaskComplexity(str, Enum):
    """Hint for the model router to pick the right provider."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
