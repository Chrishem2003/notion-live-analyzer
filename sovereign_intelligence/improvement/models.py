from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ImprovementAction:

    title: str

    description: str

    priority: str = "medium"

    target_dimension: str | None = None

    expected_impact: float = 0.0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class ImprovementPlan:

    objective: str

    current_score: float

    target_score: float

    actions: list[ImprovementAction] = field(
        default_factory=list
    )

    rationale: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )
