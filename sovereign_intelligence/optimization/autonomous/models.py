from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OptimizationCandidate:
    strategy: str
    problem_type: str
    expected_score: float
    confidence: float
    rank: int
    reason: str = ""


@dataclass
class OptimizationResult:
    strategy: str
    problem_type: str
    previous_score: float
    new_score: float
    improvement: float
    optimized: bool
    confidence: float
    candidates: list[OptimizationCandidate] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
