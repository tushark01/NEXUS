"""Base agent — abstract class for all agent types in the swarm."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from nexus.llm.router import ModelRouter
from nexus.llm.schemas import LLMRequest, Message, TaskComplexity
from nexus.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    RESEARCHER = "researcher"
    CRITIC = "critic"
    COORDINATOR = "coordinator"


class AgentState(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    SUSPENDED = "suspended"


class AgentMessage:
    """A message between agents."""

    def __init__(
        self,
        from_agent: str,
        to_agent: str,
        content: Any,
        msg_type: str = "generic",
        in_reply_to: str | None = None,
    ) -> None:
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.content = content
        self.msg_type = msg_type
        self.in_reply_to = in_reply_to


class BaseAgent(ABC):
    """Abstract base for all agent types in the NEXUS swarm."""

    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        llm: ModelRouter,
        memory: MemoryManager,
    ) -> None:
        self.agent_id = agent_id
        self.role = role
        self.state = AgentState.IDLE
        self.llm = llm
        self.memory = memory
        self._inbox: asyncio.Queue[AgentMessage] = asyncio.Queue()

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the role-specific system prompt for this agent."""

    @abstractmethod
    async def process_task(self, task_description: str, context: str = "") -> str:
        """Process a task and return the result as a string."""

    async def think(
        self,
        prompt: str,
        context: str = "",
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
    ) -> str:
        """Use the LLM to think about something — the core agent capability."""
        messages = [
            Message(role="system", content=self.get_system_prompt()),
        ]
        if context:
            messages.append(Message(role="system", content=f"Context:\n{context}"))
        messages.append(Message(role="user", content=prompt))

        response = await self.llm.complete(
            LLMRequest(messages=messages),
            hint=complexity,
        )
        return response.content

    async def send_message(self, to_agent: str, content: Any, msg_type: str = "generic") -> None:
        """Send a message — will be routed by the message bus."""
        # This is a placeholder; the orchestrator handles actual routing
        pass

    async def receive_message(self, timeout: float = 30.0) -> AgentMessage | None:
        """Wait for and return the next message."""
        try:
            return await asyncio.wait_for(self._inbox.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
