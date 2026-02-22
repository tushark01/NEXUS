"""Critic agent — reviews and validates output from other agents."""

from __future__ import annotations

import logging

from nexus.agents.base import AgentRole, BaseAgent
from nexus.llm.schemas import TaskComplexity

logger = logging.getLogger(__name__)

CRITIC_SYSTEM_PROMPT = """\
You are the NEXUS Critic Agent. Your job is to review output from other agents \
and ensure quality, accuracy, and completeness.

Guidelines:
- Check for factual accuracy and logical consistency.
- Identify gaps, errors, or areas for improvement.
- Be constructive — suggest specific improvements.
- Rate the overall quality (excellent / good / needs improvement).
- If the output is good, say so clearly and briefly.
- Focus on substance, not style."""


class CriticAgent(BaseAgent):
    """Reviews and validates output from other agents."""

    def __init__(self, agent_id: str, **kwargs: object) -> None:
        super().__init__(agent_id=agent_id, role=AgentRole.CRITIC, **kwargs)  # type: ignore[arg-type]

    def get_system_prompt(self) -> str:
        return CRITIC_SYSTEM_PROMPT

    async def process_task(self, task_description: str, context: str = "") -> str:
        """Review output and provide critique."""
        prompt = f"Review the following output:\n\n{task_description}"
        return await self.think(prompt, context, TaskComplexity.MEDIUM)

    async def review(self, original_task: str, output: str) -> str:
        """Review the output of a specific task."""
        prompt = (
            f"Original task: {original_task}\n\n"
            f"Agent output:\n{output}\n\n"
            "Provide a brief quality assessment. Is this output accurate, complete, "
            "and well-structured? If it needs improvement, suggest specific changes."
        )
        return await self.think(prompt, complexity=TaskComplexity.MEDIUM)
