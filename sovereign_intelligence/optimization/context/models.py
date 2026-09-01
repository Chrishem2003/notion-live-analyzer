from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProblemContext:
    """Normalized context describing a problem."""

    problem_type: str
    complexity: float
    requires_reasoning: bool
    requires_code: bool
    requires_research: bool
    requires_planning: bool
    requires_analysis: bool
    keywords: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
