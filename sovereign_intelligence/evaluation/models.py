from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvaluationDimension:

    name: str
    score: float
    reason: str = ""


@dataclass
class EvaluationResult:

    overall_score: float

    passed: bool

    dimensions: list[EvaluationDimension] = field(
        default_factory=list
    )

    strengths: list[str] = field(
        default_factory=list
    )

    weaknesses: list[str] = field(
        default_factory=list
    )

    recommendations: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )
