"""Executor agent — carries out tasks by using skills and LLM reasoning."""

from __future__ import annotations

import logging

from nexus.agents.base import AgentRole, BaseAgent
from nexus.llm.schemas import TaskComplexity

logger = logging.getLogger(__name__)

EXECUTOR_SYSTEM_PROMPT = """\
You are the NEXUS Executor Agent. Your job is to carry out specific tasks \
to the best of your ability. You receive task descriptions and should \
produce high-quality output.

Guidelines:
- Be thorough and precise in your execution.
- If the task involves writing, produce polished output.
- If the task involves analysis, be comprehensive.
- If you need information you don't have, say so clearly.
- Include relevant details and structure your output well."""


class ExecutorAgent(BaseAgent):
    """Carries out tasks using LLM reasoning and available skills."""

    def __init__(self, agent_id: str, **kwargs: object) -> None:
        super().__init__(agent_id=agent_id, role=AgentRole.EXECUTOR, **kwargs)  # type: ignore[arg-type]

    def get_system_prompt(self) -> str:
        return EXECUTOR_SYSTEM_PROMPT

    async def process_task(self, task_description: str, context: str = "") -> str:
        """Execute a task and return the result."""
        prompt = f"Execute this task:\n\n{task_description}"
        return await self.think(prompt, context, TaskComplexity.MEDIUM)
