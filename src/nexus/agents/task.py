"""Task model and DAG — manages task decomposition and dependencies."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """A single task in the swarm's work queue."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    parent_id: str | None = None
    depends_on: list[str] = []
    assigned_to: str | None = None
    preferred_role: str | None = None
    result: Any = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class TaskDAG:
    """Manages a directed acyclic graph of tasks with dependency tracking."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        """Add a task to the DAG."""
        self._tasks[task.id] = task

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def get_ready_tasks(self) -> list[Task]:
        """Return tasks whose dependencies are all completed and that are still pending."""
        ready = []
        for task in self._tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            # Check all dependencies are completed
            deps_met = all(
                self._tasks.get(dep_id) is not None
                and self._tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.depends_on
            )
            if deps_met:
                ready.append(task)
        return ready

    def mark_in_progress(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.IN_PROGRESS

    def mark_completed(self, task_id: str, result: Any = None) -> list[Task]:
        """Mark a task complete and return newly-unblocked tasks."""
        task = self._tasks.get(task_id)
        if not task:
            return []

        task.status = TaskStatus.COMPLETED
        task.result = result
        task.completed_at = datetime.now(timezone.utc)

        # Find tasks that were waiting on this one
        return self.get_ready_tasks()

    def mark_failed(self, task_id: str, error: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = datetime.now(timezone.utc)

    @property
    def all_tasks(self) -> list[Task]:
        return list(self._tasks.values())

    @property
    def is_complete(self) -> bool:
        """True if all tasks are completed or failed."""
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
            for t in self._tasks.values()
        )

    def get_results(self) -> dict[str, Any]:
        """Return a mapping of task_id -> result for completed tasks."""
        return {
            t.id: t.result
            for t in self._tasks.values()
            if t.status == TaskStatus.COMPLETED and t.result is not None
        }

    def summary(self) -> str:
        """Return a human-readable summary of the DAG."""
        lines = []
        for t in self._tasks.values():
            status_icon = {
                TaskStatus.PENDING: "[ ]",
                TaskStatus.IN_PROGRESS: "[~]",
                TaskStatus.COMPLETED: "[x]",
                TaskStatus.FAILED: "[!]",
                TaskStatus.CANCELLED: "[-]",
            }.get(t.status, "[?]")
            deps = f" (depends on: {', '.join(t.depends_on)})" if t.depends_on else ""
            assigned = f" -> {t.assigned_to}" if t.assigned_to else ""
            lines.append(f"  {status_icon} {t.id[:8]}: {t.title}{deps}{assigned}")
        return "\n".join(lines)
