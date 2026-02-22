"""Agent message bus — routes messages between agents in the swarm."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable

from nexus.agents.base import AgentMessage, BaseAgent
from nexus.core.event_bus import EventBus
from nexus.core.events import Event

logger = logging.getLogger(__name__)


class AgentMessageEvent(Event):
    """An agent-to-agent message was sent."""

    event_type: str = "agent_message"
    from_agent: str
    to_agent: str
    msg_type: str
    content: Any = None


MessageHandler = Callable[[AgentMessage], Awaitable[None]]


class MessageBus:
    """Routes messages between agents with optional broadcast and topic subscriptions.

    Features:
    - Direct agent-to-agent messaging (delivered to inbox queue)
    - Broadcast to all agents
    - Topic-based pub/sub for agent groups
    - Dead letter queue for undeliverable messages
    - Event bus integration for observability
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._topics: dict[str, set[str]] = defaultdict(set)
        self._dead_letters: list[AgentMessage] = []
        self._event_bus = event_bus
        self._message_count = 0

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent so it can send/receive messages."""
        self._agents[agent.agent_id] = agent

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the bus."""
        self._agents.pop(agent_id, None)
        for subscribers in self._topics.values():
            subscribers.discard(agent_id)

    def subscribe_topic(self, agent_id: str, topic: str) -> None:
        """Subscribe an agent to a topic for group messaging."""
        self._topics[topic].add(agent_id)

    def unsubscribe_topic(self, agent_id: str, topic: str) -> None:
        """Unsubscribe an agent from a topic."""
        self._topics[topic].discard(agent_id)

    async def send(self, message: AgentMessage) -> bool:
        """Send a message to a specific agent. Returns True if delivered."""
        self._message_count += 1

        target = self._agents.get(message.to_agent)
        if not target:
            logger.warning(
                "Message from %s to unknown agent %s — dead-lettered",
                message.from_agent,
                message.to_agent,
            )
            self._dead_letters.append(message)
            return False

        await target._inbox.put(message)

        # Publish event for observability
        if self._event_bus:
            await self._event_bus.publish(
                AgentMessageEvent(
                    source="message_bus",
                    from_agent=message.from_agent,
                    to_agent=message.to_agent,
                    msg_type=message.msg_type,
                )
            )

        logger.debug(
            "Delivered [%s] from %s -> %s",
            message.msg_type,
            message.from_agent,
            message.to_agent,
        )
        return True

    async def broadcast(self, from_agent: str, content: Any, msg_type: str = "broadcast") -> int:
        """Send a message to all registered agents (except sender). Returns delivery count."""
        delivered = 0
        for agent_id, agent in self._agents.items():
            if agent_id == from_agent:
                continue
            msg = AgentMessage(
                from_agent=from_agent,
                to_agent=agent_id,
                content=content,
                msg_type=msg_type,
            )
            await agent._inbox.put(msg)
            delivered += 1
        return delivered

    async def publish_to_topic(
        self, from_agent: str, topic: str, content: Any, msg_type: str = "topic"
    ) -> int:
        """Send a message to all agents subscribed to a topic. Returns delivery count."""
        subscribers = self._topics.get(topic, set())
        delivered = 0
        for agent_id in subscribers:
            if agent_id == from_agent:
                continue
            agent = self._agents.get(agent_id)
            if agent:
                msg = AgentMessage(
                    from_agent=from_agent,
                    to_agent=agent_id,
                    content=content,
                    msg_type=msg_type,
                )
                await agent._inbox.put(msg)
                delivered += 1
        return delivered

    @property
    def registered_agents(self) -> list[str]:
        return list(self._agents.keys())

    @property
    def message_count(self) -> int:
        return self._message_count

    @property
    def dead_letter_count(self) -> int:
        return len(self._dead_letters)

    def status_summary(self) -> str:
        lines = [
            f"Registered agents: {len(self._agents)}",
            f"Messages routed: {self._message_count}",
            f"Dead letters: {len(self._dead_letters)}",
            f"Topics: {list(self._topics.keys()) or 'none'}",
        ]
        return "\n".join(lines)
