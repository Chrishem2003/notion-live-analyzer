from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StrategyScore:
    strategy: str
    problem_type: str
    score: float
    confidence: float
    samples: int
    success_rate: float
    average_improvement: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningDecision:
    strategy: str
    problem_type: str
    confidence: float
    reason: str
    ranked: list[StrategyScore] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
