from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Action:

    kind: str

    target: str

    arguments: dict[str, Any] = field(
        default_factory=dict
    )

    reason: str = ""


@dataclass
class ActionResult:

    action: Action

    success: bool

    output: Any = None

    error: str | None = None


@dataclass
class AutonomousState:

    objective: str

    completed_actions: list[ActionResult] = field(
        default_factory=list
    )

    observations: list[str] = field(
        default_factory=list
    )

    iteration: int = 0

    status: str = "running"


@dataclass
class AutonomousResult:

    success: bool

    answer: str

    iterations: int

    actions: list[ActionResult] = field(
        default_factory=list
    )

    observations: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )
