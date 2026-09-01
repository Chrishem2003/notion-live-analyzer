from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionPolicy:

    max_retries: int = 2
    timeout_seconds: float = 120.0
    stop_on_failure: bool = True
    max_parallel_tasks: int = 4


@dataclass
class TaskExecutionRecord:

    task_id: str
    attempt: int
    status: str

    started_at: str
    finished_at: str | None = None

    duration_seconds: float | None = None

    result: Any = None
    error: str | None = None


@dataclass
class ExecutionReport:

    status: str

    completed: list[str] = field(
        default_factory=list
    )

    failed: list[str] = field(
        default_factory=list
    )

    skipped: list[str] = field(
        default_factory=list
    )

    records: list[TaskExecutionRecord] = field(
        default_factory=list
    )
