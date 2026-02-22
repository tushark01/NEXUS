"""NEXUS event type hierarchy — all components communicate through typed events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid4().hex


class Event(BaseModel):
    """Base event — all NEXUS events inherit from this."""

    id: str = Field(default_factory=_new_id)
    timestamp: datetime = Field(default_factory=_utcnow)
    source: str = "system"


class UserMessageEvent(Event):
    """User sent a message through any interface."""

    event_type: Literal["user_message"] = "user_message"
    content: str
    session_id: str
    interface: str  # "cli", "api", "telegram", "discord"


class AgentResponseEvent(Event):
    """An agent produced a response."""

    event_type: Literal["agent_response"] = "agent_response"
    content: str
    agent_id: str
    session_id: str
    task_id: str | None = None


class StreamChunkEvent(Event):
    """A streaming chunk of LLM output."""

    event_type: Literal["stream_chunk"] = "stream_chunk"
    content: str
    session_id: str
    is_final: bool = False


class TaskCreatedEvent(Event):
    """A new task was created in the swarm."""

    event_type: Literal["task_created"] = "task_created"
    task_id: str
    title: str
    parent_id: str | None = None


class TaskCompletedEvent(Event):
    """A task completed execution."""

    event_type: Literal["task_completed"] = "task_completed"
    task_id: str
    result: Any = None
    success: bool = True


class SkillInvocationEvent(Event):
    """A skill was invoked by an agent."""

    event_type: Literal["skill_invocation"] = "skill_invocation"
    skill_name: str
    arguments: dict[str, Any] = {}
    agent_id: str
    result: Any = None
    success: bool = True


class MemoryStoreEvent(Event):
    """Something was stored in memory."""

    event_type: Literal["memory_store"] = "memory_store"
    memory_type: Literal["working", "episodic", "semantic"]
    content: str
    metadata: dict[str, Any] = {}


class SecurityAuditEvent(Event):
    """A security-relevant action occurred."""

    event_type: Literal["security_audit"] = "security_audit"
    action: str
    actor: str
    resource: str
    result: Literal["allowed", "denied", "error"]
    details: dict[str, Any] = {}


class AgentSpawnedEvent(Event):
    """A new agent was spawned in the pool."""

    event_type: Literal["agent_spawned"] = "agent_spawned"
    agent_id: str
    role: str


class ErrorEvent(Event):
    """An error occurred in the system."""

    event_type: Literal["error"] = "error"
    error_type: str
    message: str
    details: dict[str, Any] = {}
