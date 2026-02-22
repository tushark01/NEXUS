"""Agent pool — manages agent lifecycle, scaling, and assignment."""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from nexus.agents.base import AgentRole, AgentState, BaseAgent
from nexus.agents.coordinator import CoordinatorAgent
from nexus.agents.critic import CriticAgent
from nexus.agents.executor import ExecutorAgent
from nexus.agents.planner import PlannerAgent
from nexus.agents.researcher import ResearcherAgent
from nexus.llm.router import ModelRouter
from nexus.memory.manager import MemoryManager

logger = logging.getLogger(__name__)

ROLE_TO_CLASS: dict[AgentRole, type[BaseAgent]] = {
    AgentRole.PLANNER: PlannerAgent,
    AgentRole.EXECUTOR: ExecutorAgent,
    AgentRole.RESEARCHER: ResearcherAgent,
    AgentRole.CRITIC: CriticAgent,
    AgentRole.COORDINATOR: CoordinatorAgent,
}


class AgentPool:
    """Manages a pool of agents for the swarm."""

    def __init__(
        self,
        llm: ModelRouter,
        memory: MemoryManager,
        max_agents: int = 5,
    ) -> None:
        self._llm = llm
        self._memory = memory
        self._max_agents = max_agents
        self._agents: dict[str, BaseAgent] = {}
        self._semaphore = asyncio.Semaphore(max_agents)

    def spawn(self, role: AgentRole) -> BaseAgent:
        """Create and register a new agent of the given role."""
        agent_id = f"{role.value}_{uuid4().hex[:6]}"
        cls = ROLE_TO_CLASS.get(role)
        if not cls:
            raise ValueError(f"Unknown agent role: {role}")

        agent = cls(agent_id=agent_id, llm=self._llm, memory=self._memory)
        self._agents[agent_id] = agent
        logger.info("Spawned agent: %s (%s)", agent_id, role.value)
        return agent

    def get(self, agent_id: str) -> BaseAgent | None:
        return self._agents.get(agent_id)

    def get_idle(self, role: AgentRole) -> BaseAgent | None:
        """Get an idle agent of the specified role."""
        for agent in self._agents.values():
            if agent.role == role and agent.state == AgentState.IDLE:
                return agent
        return None

    def acquire(self, role: AgentRole) -> BaseAgent:
        """Get an idle agent of the preferred role, or spawn one."""
        agent = self.get_idle(role)
        if agent:
            agent.state = AgentState.WORKING
            return agent
        # Spawn a new one
        agent = self.spawn(role)
        agent.state = AgentState.WORKING
        return agent

    def release(self, agent_id: str) -> None:
        """Return agent to idle state."""
        agent = self._agents.get(agent_id)
        if agent:
            agent.state = AgentState.IDLE

    def all_agents(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def status_summary(self) -> str:
        """Return a summary of all agents and their states."""
        if not self._agents:
            return "No agents in pool."
        lines = []
        for agent in self._agents.values():
            lines.append(f"  {agent.agent_id} [{agent.role.value}] — {agent.state.value}")
        return "\n".join(lines)
