"""Swarm orchestrator — the master conductor that runs multi-agent task execution."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

from nexus.agents.base import AgentMessage, AgentRole, AgentState, BaseAgent
from nexus.agents.consensus import ConsensusEngine, ConsensusStrategy, VoteType
from nexus.agents.coordinator import CoordinatorAgent
from nexus.agents.message_bus import MessageBus
from nexus.agents.pool import AgentPool
from nexus.agents.task import Task, TaskDAG, TaskStatus
from nexus.core.event_bus import EventBus
from nexus.core.events import TaskCompletedEvent, TaskCreatedEvent
from nexus.llm.router import ModelRouter
from nexus.memory.manager import MemoryManager

logger = logging.getLogger(__name__)

# Map role strings from planner output to AgentRole enum
ROLE_MAP: dict[str, AgentRole] = {
    "planner": AgentRole.PLANNER,
    "executor": AgentRole.EXECUTOR,
    "researcher": AgentRole.RESEARCHER,
    "critic": AgentRole.CRITIC,
    "coordinator": AgentRole.COORDINATOR,
}


class SwarmUpdate:
    """A progress update from the swarm for streaming to the UI."""

    def __init__(
        self,
        update_type: str,
        content: str,
        task_id: str | None = None,
        agent_id: str | None = None,
        is_final: bool = False,
    ) -> None:
        self.update_type = update_type  # "status", "task_start", "task_done", "result", "error"
        self.content = content
        self.task_id = task_id
        self.agent_id = agent_id
        self.is_final = is_final


class SwarmOrchestrator:
    """The master conductor — coordinates multi-agent goal execution.

    Flow:
    1. User submits a goal
    2. Coordinator evaluates: direct (single LLM call) or swarm (multi-agent)
    3. For swarm: Planner decomposes goal -> TaskDAG
    4. Orchestrator executes tasks in parallel (respecting dependencies)
    5. Critic reviews results if quality check is enabled
    6. Coordinator synthesizes final answer
    """

    def __init__(
        self,
        llm: ModelRouter,
        memory: MemoryManager,
        event_bus: EventBus | None = None,
        max_agents: int = 5,
        enable_critic: bool = True,
    ) -> None:
        self._llm = llm
        self._memory = memory
        self._event_bus = event_bus
        self._pool = AgentPool(llm=llm, memory=memory, max_agents=max_agents)
        self._message_bus = MessageBus(event_bus=event_bus)
        self._consensus = ConsensusEngine(ConsensusStrategy.MAJORITY)
        self._enable_critic = enable_critic

        # Spawn the coordinator
        self._coordinator: CoordinatorAgent = self._pool.spawn(AgentRole.COORDINATOR)  # type: ignore[assignment]
        self._message_bus.register_agent(self._coordinator)

    async def execute_goal(self, goal: str, context: str = "") -> AsyncIterator[SwarmUpdate]:
        """Execute a goal, yielding progress updates.

        This is the main entry point — call this from the CLI/API.
        """
        yield SwarmUpdate("status", "Evaluating goal complexity...")

        # Step 1: Coordinator evaluates the goal
        evaluation = await self._coordinator.evaluate_goal(goal)
        strategy = evaluation.get("strategy", "direct")
        reasoning = evaluation.get("reasoning", "")

        yield SwarmUpdate(
            "status",
            f"Strategy: **{strategy}** — {reasoning}",
        )

        if strategy == "direct":
            # Simple goal — handle with a clean LLM call (not the coordinator's JSON prompt)
            yield SwarmUpdate("status", "Handling directly...")
            from nexus.llm.schemas import LLMRequest, Message, TaskComplexity

            direct_messages = [
                Message(
                    role="system",
                    content="You are NEXUS, a hyper-intelligent AI assistant. Be helpful, precise, and thorough.",
                ),
            ]
            if context:
                direct_messages.append(Message(role="system", content=f"Context:\n{context}"))
            direct_messages.append(Message(role="user", content=goal))

            response = await self._llm.complete(
                LLMRequest(messages=direct_messages),
                hint=TaskComplexity.MEDIUM,
            )
            yield SwarmUpdate("result", response.content, is_final=True)
            return

        # Step 2: Planner decomposes into TaskDAG
        yield SwarmUpdate("status", "Decomposing goal into tasks...")
        planner = self._pool.acquire(AgentRole.PLANNER)
        self._message_bus.register_agent(planner)

        from nexus.agents.planner import PlannerAgent

        dag = await PlannerAgent.decompose(planner, goal, context)  # type: ignore[arg-type]
        self._pool.release(planner.agent_id)

        # Publish task creation events
        for task in dag.all_tasks:
            if self._event_bus:
                await self._event_bus.publish(
                    TaskCreatedEvent(
                        source="orchestrator",
                        task_id=task.id,
                        title=task.title,
                    )
                )

        yield SwarmUpdate("status", f"Plan created: {len(dag.all_tasks)} tasks\n{dag.summary()}")

        # Step 3: Execute tasks in parallel waves (respecting dependencies)
        final_results: dict[str, str] = {}

        while not dag.is_complete:
            ready = dag.get_ready_tasks()
            if not ready:
                # Check for deadlock
                remaining = [t for t in dag.all_tasks if t.status == TaskStatus.PENDING]
                if remaining:
                    yield SwarmUpdate("error", "Deadlock detected — some tasks have unmet dependencies")
                    for t in remaining:
                        dag.mark_failed(t.id, "Deadlock — unresolvable dependencies")
                break

            # Launch all ready tasks concurrently
            yield SwarmUpdate(
                "status",
                f"Executing wave: {', '.join(t.title for t in ready)}",
            )

            results = await asyncio.gather(
                *(self._execute_task(task, dag, context) for task in ready),
                return_exceptions=True,
            )

            # Process results
            for task, result in zip(ready, results):
                if isinstance(result, Exception):
                    dag.mark_failed(task.id, str(result))
                    yield SwarmUpdate("error", f"Task '{task.title}' failed: {result}", task_id=task.id)
                else:
                    final_results[task.id] = result
                    newly_ready = dag.mark_completed(task.id, result)
                    yield SwarmUpdate(
                        "task_done",
                        f"Completed: {task.title}",
                        task_id=task.id,
                    )
                    if self._event_bus:
                        await self._event_bus.publish(
                            TaskCompletedEvent(
                                source="orchestrator",
                                task_id=task.id,
                                result=result[:200] if isinstance(result, str) else str(result)[:200],
                            )
                        )

        # Step 4: Optional critic review
        if self._enable_critic and final_results:
            yield SwarmUpdate("status", "Critic reviewing results...")
            critic = self._pool.acquire(AgentRole.CRITIC)
            self._message_bus.register_agent(critic)

            from nexus.agents.critic import CriticAgent

            review = await CriticAgent.review(  # type: ignore[arg-type]
                critic,
                goal,
                "\n\n".join(f"**{tid}**: {res[:300]}" for tid, res in final_results.items()),
            )
            self._pool.release(critic.agent_id)
            yield SwarmUpdate("status", f"Critic says: {review[:200]}")

        # Step 5: Coordinator synthesizes final answer
        yield SwarmUpdate("status", "Synthesizing final answer...")
        final = await self._coordinator.synthesize_results(goal, final_results)
        yield SwarmUpdate("result", final, is_final=True)

    async def _execute_task(self, task: Task, dag: TaskDAG, context: str) -> str:
        """Execute a single task using the appropriate agent."""
        dag.mark_in_progress(task.id)
        task.status = TaskStatus.IN_PROGRESS

        # Determine the agent role
        role_str = task.preferred_role or "executor"
        role = ROLE_MAP.get(role_str, AgentRole.EXECUTOR)

        # Acquire an agent
        agent = self._pool.acquire(role)
        task.assigned_to = agent.agent_id
        self._message_bus.register_agent(agent)

        # Build context from dependency results
        dep_context = context
        for dep_id in task.depends_on:
            dep_task = dag.get_task(dep_id)
            if dep_task and dep_task.result:
                dep_context += f"\n\n--- Result from '{dep_task.title}' ---\n{dep_task.result}"

        try:
            result = await agent.process_task(task.description, dep_context)
            return result
        finally:
            self._pool.release(agent.agent_id)

    @property
    def pool(self) -> AgentPool:
        return self._pool

    @property
    def message_bus(self) -> MessageBus:
        return self._message_bus

    @property
    def consensus(self) -> ConsensusEngine:
        return self._consensus

    def status_summary(self) -> str:
        """Return a summary of the swarm state."""
        return (
            f"=== NEXUS Swarm ===\n"
            f"{self._pool.status_summary()}\n\n"
            f"Message Bus:\n{self._message_bus.status_summary()}\n\n"
            f"Consensus:\n{self._consensus.summary()}"
        )
