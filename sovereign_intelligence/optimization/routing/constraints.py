from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoutingConstraints:
    """Constraints applied before dynamic strategy selection."""

    required_capabilities: set[str] = field(default_factory=set)
    forbidden_strategies: set[str] = field(default_factory=set)
    preferred_strategies: list[str] = field(default_factory=list)

    minimum_confidence: float | None = None
    maximum_complexity: float | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.minimum_confidence is not None:
            if not 0.0 <= self.minimum_confidence <= 1.0:
                raise ValueError(
                    "minimum_confidence must be between 0 and 1."
                )

        if self.maximum_complexity is not None:
            if not 0.0 <= self.maximum_complexity <= 1.0:
                raise ValueError(
                    "maximum_complexity must be between 0 and 1."
                )

        self.required_capabilities = {
            str(value).strip().lower()
            for value in self.required_capabilities
            if str(value).strip()
        }

        self.forbidden_strategies = {
            str(value).strip().lower()
            for value in self.forbidden_strategies
            if str(value).strip()
        }

        self.preferred_strategies = [
            str(value).strip().lower()
            for value in self.preferred_strategies
            if str(value).strip()
        ]


@dataclass
class ConstraintEvaluation:
    strategy: str
    eligible: bool
    reason: str
    preference_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
