from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunEvent:

    name: str

    status: str

    timestamp: str = field(
        default_factory=utc_now
    )

    data: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class IntelligenceRun:

    id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    started_at: str = field(
        default_factory=utc_now
    )

    completed_at: str | None = None

    status: str = "running"

    events: list[RunEvent] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    error: str | None = None

    def add_event(
        self,
        name: str,
        status: str,
        data: dict[str, Any] | None = None,
    ):

        self.events.append(
            RunEvent(
                name=name,
                status=status,
                data=data or {},
            )
        )

    def complete(
        self,
        status: str = "completed",
        error: str | None = None,
    ):

        self.status = status

        self.error = error

        self.completed_at = utc_now()
