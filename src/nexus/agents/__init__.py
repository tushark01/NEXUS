"""NEXUS multi-agent swarm system."""

from nexus.agents.base import AgentMessage, AgentRole, AgentState, BaseAgent
from nexus.agents.consensus import ConsensusEngine, ConsensusStrategy
from nexus.agents.coordinator import CoordinatorAgent
from nexus.agents.message_bus import MessageBus
from nexus.agents.orchestrator import SwarmOrchestrator, SwarmUpdate
from nexus.agents.pool import AgentPool
from nexus.agents.task import Task, TaskDAG, TaskStatus

__all__ = [
    "AgentMessage",
    "AgentPool",
    "AgentRole",
    "AgentState",
    "BaseAgent",
    "ConsensusEngine",
    "ConsensusStrategy",
    "CoordinatorAgent",
    "MessageBus",
    "SwarmOrchestrator",
    "SwarmUpdate",
    "Task",
    "TaskDAG",
    "TaskStatus",
]
