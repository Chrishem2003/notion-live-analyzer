from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StrategyOutcome:

    strategy: str

    success: bool

    score: float

    attempts: int = 1

    problem_type: str = "general"

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class StrategyProfile:

    strategy: str

    trials: int = 0

    successes: int = 0

    total_score: float = 0.0

    average_score: float = 0.0

    success_rate: float = 0.0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class OptimizationDecision:

    strategy: str

    confidence: float

    reason: str = ""

    alternatives: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )
