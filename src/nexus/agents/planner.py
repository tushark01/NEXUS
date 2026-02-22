"""Planner agent — decomposes goals into task DAGs."""

from __future__ import annotations

import json
import logging

from nexus.agents.base import AgentRole, BaseAgent
from nexus.agents.task import Task, TaskDAG
from nexus.llm.schemas import TaskComplexity

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """\
You are the NEXUS Planner Agent. Your job is to decompose complex goals into \
a directed acyclic graph (DAG) of smaller, actionable tasks.

Rules:
1. Each task should be small enough for a single agent to complete.
2. Tasks can depend on other tasks (the depend_on field).
3. Independent tasks should NOT depend on each other so they can run in parallel.
4. Assign a preferred_role: "researcher" for information gathering, \
"executor" for actions/writing, "critic" for review/validation.
5. Keep the plan focused — don't over-decompose simple goals.

For simple goals (1-2 steps), return just 1-2 tasks.
For complex goals, return up to 6 tasks.

Return a JSON array of task objects:
[
  {
    "id": "t1",
    "title": "Short task title",
    "description": "What needs to be done in detail",
    "depends_on": [],
    "preferred_role": "researcher"
  },
  {
    "id": "t2",
    "title": "Another task",
    "description": "Details...",
    "depends_on": ["t1"],
    "preferred_role": "executor"
  }
]

Return ONLY the JSON array, no other text."""


class PlannerAgent(BaseAgent):
    """Decomposes high-level goals into executable task DAGs."""

    def __init__(self, agent_id: str, **kwargs: object) -> None:
        super().__init__(agent_id=agent_id, role=AgentRole.PLANNER, **kwargs)  # type: ignore[arg-type]

    def get_system_prompt(self) -> str:
        return PLANNER_SYSTEM_PROMPT

    async def process_task(self, task_description: str, context: str = "") -> str:
        return await self.think(task_description, context, TaskComplexity.COMPLEX)

    async def decompose(self, goal: str, context: str = "") -> TaskDAG:
        """Decompose a goal into a TaskDAG."""
        prompt = f"Decompose this goal into tasks:\n\n{goal}"

        response = await self.think(prompt, context, TaskComplexity.COMPLEX)

        # Parse JSON response
        dag = TaskDAG()
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = response
            if "```" in json_str:
                start = json_str.find("[")
                end = json_str.rfind("]") + 1
                if start >= 0 and end > start:
                    json_str = json_str[start:end]

            tasks_data = json.loads(json_str)

            for td in tasks_data:
                task = Task(
                    id=td.get("id", ""),
                    title=td.get("title", ""),
                    description=td.get("description", ""),
                    depends_on=td.get("depends_on", []),
                    preferred_role=td.get("preferred_role"),
                )
                dag.add_task(task)

            logger.info("Planner decomposed goal into %d tasks", len(dag.all_tasks))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Fallback: create a single task for the whole goal
            logger.warning("Failed to parse planner output: %s. Using single task.", e)
            dag.add_task(
                Task(
                    title="Execute goal",
                    description=goal,
                    preferred_role="executor",
                )
            )

        return dag
