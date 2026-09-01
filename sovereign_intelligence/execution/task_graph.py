from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskNode:

    id: str
    title: str
    objective: str

    agent: str = "general"

    dependencies: list[str] = field(
        default_factory=list
    )

    tools: list[str] = field(
        default_factory=list
    )

    priority: int = 100

    status: str = "pending"

    result: Any = None

    error: str | None = None


@dataclass
class TaskGraph:

    objective: str

    tasks: list[TaskNode] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def get(self, task_id: str) -> TaskNode | None:

        for task in self.tasks:

            if task.id == task_id:
                return task

        return None
