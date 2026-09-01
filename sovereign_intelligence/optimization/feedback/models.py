from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StrategyFeedback:

    strategy: str

    problem_type: str

    score: float

    success: bool

    improvement: float = 0.0

    baseline_score: float = 0.0

    final_score: float = 0.0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class FeedbackSummary:

    strategy: str

    problem_type: str

    samples: int

    successes: int

    average_score: float

    average_improvement: float

    success_rate: float

    metadata: dict[str, Any] = field(
        default_factory=dict
    )
