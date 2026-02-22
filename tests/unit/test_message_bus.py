"""Tests for the MessageBus."""

import asyncio

import pytest

from nexus.agents.base import AgentMessage, AgentRole, BaseAgent
from nexus.agents.message_bus import MessageBus
from nexus.llm.router import ModelRouter
from nexus.llm.schemas import TaskComplexity
from nexus.memory.manager import MemoryManager
from nexus.memory.working import WorkingMemory


class DummyAgent(BaseAgent):
    """Minimal agent for testing."""

    def __init__(self, agent_id: str):
        # Create minimal dependencies
        router = ModelRouter.__new__(ModelRouter)
        router._providers = {}
        router._fallback_chains = {}
        router._default_provider = "none"

        memory = MemoryManager(working=WorkingMemory())

        super().__init__(
            agent_id=agent_id,
            role=AgentRole.EXECUTOR,
            llm=router,
            memory=memory,
        )

    def get_system_prompt(self) -> str:
        return "test"

    async def process_task(self, task_description: str, context: str = "") -> str:
        return "done"


class TestMessageBus:
    @pytest.mark.asyncio
    async def test_register_and_send(self):
        bus = MessageBus()
        agent = DummyAgent("agent_a")
        bus.register_agent(agent)

        msg = AgentMessage(from_agent="ext", to_agent="agent_a", content="hello")
        result = await bus.send(msg)
        assert result is True

        received = await agent.receive_message(timeout=1.0)
        assert received is not None
        assert received.content == "hello"

    @pytest.mark.asyncio
    async def test_send_to_unknown_agent(self):
        bus = MessageBus()
        msg = AgentMessage(from_agent="a", to_agent="unknown", content="hi")
        result = await bus.send(msg)
        assert result is False
        assert bus.dead_letter_count == 1

    @pytest.mark.asyncio
    async def test_broadcast(self):
        bus = MessageBus()
        a1 = DummyAgent("a1")
        a2 = DummyAgent("a2")
        a3 = DummyAgent("a3")
        bus.register_agent(a1)
        bus.register_agent(a2)
        bus.register_agent(a3)

        count = await bus.broadcast("a1", "hello everyone")
        assert count == 2  # a2 and a3, not a1

        m2 = await a2.receive_message(timeout=1.0)
        m3 = await a3.receive_message(timeout=1.0)
        assert m2 is not None
        assert m3 is not None
        assert m2.content == "hello everyone"

    @pytest.mark.asyncio
    async def test_topic_subscription(self):
        bus = MessageBus()
        a1 = DummyAgent("a1")
        a2 = DummyAgent("a2")
        a3 = DummyAgent("a3")
        bus.register_agent(a1)
        bus.register_agent(a2)
        bus.register_agent(a3)

        bus.subscribe_topic("a1", "research")
        bus.subscribe_topic("a2", "research")
        # a3 not subscribed

        count = await bus.publish_to_topic("a3", "research", "findings")
        assert count == 2

        m1 = await a1.receive_message(timeout=1.0)
        assert m1 is not None
        assert m1.content == "findings"

    @pytest.mark.asyncio
    async def test_unregister(self):
        bus = MessageBus()
        agent = DummyAgent("a1")
        bus.register_agent(agent)
        assert "a1" in bus.registered_agents

        bus.unregister_agent("a1")
        assert "a1" not in bus.registered_agents

    def test_status_summary(self):
        bus = MessageBus()
        s = bus.status_summary()
        assert "Registered agents" in s
