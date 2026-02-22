"""Researcher agent — gathers and synthesizes information."""

from __future__ import annotations

import logging

from nexus.agents.base import AgentRole, BaseAgent
from nexus.llm.schemas import TaskComplexity

logger = logging.getLogger(__name__)

RESEARCHER_SYSTEM_PROMPT = """\
You are the NEXUS Researcher Agent. Your job is to gather, analyze, and \
synthesize information on given topics.

Guidelines:
- Provide comprehensive, well-structured research findings.
- Distinguish between facts and analysis.
- Cite sources when relevant.
- Highlight key insights and patterns.
- Present findings in a clear, organized manner.
- If you don't have enough information, clearly state what's missing."""


class ResearcherAgent(BaseAgent):
    """Gathers and synthesizes information for research tasks."""

    def __init__(self, agent_id: str, **kwargs: object) -> None:
        super().__init__(agent_id=agent_id, role=AgentRole.RESEARCHER, **kwargs)  # type: ignore[arg-type]

    def get_system_prompt(self) -> str:
        return RESEARCHER_SYSTEM_PROMPT

    async def process_task(self, task_description: str, context: str = "") -> str:
        """Research a topic and return findings."""
        prompt = f"Research the following:\n\n{task_description}"
        return await self.think(prompt, context, TaskComplexity.COMPLEX)
