"""Coordinator agent — the brain of the swarm that orchestrates multi-agent collaboration."""

from __future__ import annotations

import json
import logging

from nexus.agents.base import AgentRole, BaseAgent
from nexus.llm.schemas import TaskComplexity

logger = logging.getLogger(__name__)

COORDINATOR_SYSTEM_PROMPT = """\
You are the NEXUS Coordinator Agent — the brain of a multi-agent swarm.

Your responsibilities:
1. Receive high-level goals from users and decide execution strategy.
2. Determine if a goal is SIMPLE (handle directly) or COMPLEX (delegate to swarm).
3. For complex goals, instruct the Planner to decompose into tasks.
4. Monitor task execution across agents.
5. Synthesize results from multiple agents into a coherent final answer.
6. Resolve conflicts when agents disagree by requesting Critic review.

When evaluating a goal, respond with JSON:
{
  "strategy": "direct" | "swarm",
  "reasoning": "why this strategy",
  "complexity": "simple" | "medium" | "complex"
}

For "direct" strategy: you'll handle it yourself with a single LLM call.
For "swarm" strategy: the Planner will decompose it and agents will execute in parallel.

Return ONLY the JSON, no other text."""


SYNTHESIS_PROMPT = """\
You are synthesizing results from multiple agents who worked on different parts of a goal.

Original goal: {goal}

Task results:
{results}

Synthesize these results into a single, coherent, well-structured response that \
fully addresses the original goal. Combine insights, remove redundancy, and ensure \
the response flows naturally. If any tasks failed, acknowledge gaps gracefully."""


class CoordinatorAgent(BaseAgent):
    """Orchestrates the swarm — decides strategy, delegates, and synthesizes."""

    def __init__(self, agent_id: str, **kwargs: object) -> None:
        super().__init__(agent_id=agent_id, role=AgentRole.COORDINATOR, **kwargs)  # type: ignore[arg-type]

    def get_system_prompt(self) -> str:
        return COORDINATOR_SYSTEM_PROMPT

    async def process_task(self, task_description: str, context: str = "") -> str:
        return await self.think(task_description, context, TaskComplexity.COMPLEX)

    async def evaluate_goal(self, goal: str) -> dict:
        """Evaluate a goal and decide on execution strategy.

        Returns:
            {"strategy": "direct"|"swarm", "reasoning": str, "complexity": str}
        """
        prompt = f"Evaluate this goal and decide the execution strategy:\n\n{goal}"
        response = await self.think(prompt, complexity=TaskComplexity.SIMPLE)

        try:
            # Parse JSON from response
            json_str = response.strip()
            if "```" in json_str:
                start = json_str.find("{")
                end = json_str.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = json_str[start:end]
            return json.loads(json_str)
        except (json.JSONDecodeError, KeyError):
            # Default to direct for unparseable responses
            logger.warning("Could not parse coordinator response, defaulting to direct")
            return {
                "strategy": "direct",
                "reasoning": "Fallback — treating as simple goal",
                "complexity": "simple",
            }

    async def synthesize_results(self, goal: str, task_results: dict[str, str]) -> str:
        """Combine results from multiple agents into a coherent response."""
        results_text = ""
        for task_id, result in task_results.items():
            results_text += f"\n### Task {task_id}:\n{result}\n"

        prompt = SYNTHESIS_PROMPT.format(goal=goal, results=results_text)

        # Use a dedicated synthesis call — NOT the coordinator system prompt
        # which would make it return JSON strategy evaluation
        from nexus.llm.schemas import LLMRequest, Message

        messages = [
            Message(
                role="system",
                content=(
                    "You are a synthesis expert. Combine the task results below into a "
                    "single, coherent, well-structured response. Write in clear prose, "
                    "use Markdown formatting, and fully address the original goal."
                ),
            ),
            Message(role="user", content=prompt),
        ]
        response = await self.llm.complete(
            LLMRequest(messages=messages),
            hint=TaskComplexity.COMPLEX,
        )
        return response.content

    async def handle_conflict(self, task_title: str, outputs: list[str]) -> str:
        """Resolve a conflict when multiple agents disagree."""
        prompt = (
            f"Multiple agents produced different results for: {task_title}\n\n"
            + "\n---\n".join(f"Output {i+1}:\n{o}" for i, o in enumerate(outputs))
            + "\n\nAnalyze the differences, determine which is most accurate, "
            "and produce the best combined result."
        )
        return await self.think(prompt, complexity=TaskComplexity.COMPLEX)
