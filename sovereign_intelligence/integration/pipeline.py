from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class PipelineEvent:
    name: str
    status: str
    timestamp: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    success: bool
    answer: str = ""
    events: list[PipelineEvent] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class IntelligencePipeline:

    def __init__(self):
        self.events = []

    def emit(self, name, status, data=None):
        event = PipelineEvent(
            name=name,
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data or {},
        )
        self.events.append(event)
        return event

    def run(self, task: Callable, *args, **kwargs):

        self.events = []

        self.emit("pipeline_started", "started")

        try:
            self.emit("task_started", "started")

            result = task(*args, **kwargs)

            self.emit("task_completed", "completed")

            answer = result if isinstance(result, str) else str(result)

            self.emit("pipeline_completed", "completed")

            return PipelineResult(
                success=True,
                answer=answer,
                events=list(self.events),
            )

        except Exception as exc:

            self.emit(
                "task_failed",
                "failed",
                {"error": str(exc)},
            )

            self.emit(
                "pipeline_failed",
                "failed",
            )

            return PipelineResult(
                success=False,
                events=list(self.events),
                error=str(exc),
            )
