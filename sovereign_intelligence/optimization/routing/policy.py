from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoutingPolicy:
    """Policy controlling dynamic strategy routing."""

    minimum_confidence: float = 0.67

    complexity_weight: float = 0.25
    confidence_weight: float = 0.25
    historical_weight: float = 0.30
    constraint_weight: float = 0.20

    allow_fallback: bool = True
    fallback_strategy: str = "direct"

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        values = {
            "minimum_confidence": self.minimum_confidence,
            "complexity_weight": self.complexity_weight,
            "confidence_weight": self.confidence_weight,
            "historical_weight": self.historical_weight,
            "constraint_weight": self.constraint_weight,
        }

        for name, value in values.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1."
                )

        if not self.fallback_strategy.strip():
            raise ValueError(
                "fallback_strategy cannot be empty."
            )

    @property
    def total_weight(self) -> float:
        return (
            self.complexity_weight
            + self.confidence_weight
            + self.historical_weight
            + self.constraint_weight
        )

    def normalized_weights(self) -> dict[str, float]:
        total = self.total_weight

        if total <= 0.0:
            raise ValueError(
                "Routing policy weights must sum to a positive value."
            )

        return {
            "complexity": self.complexity_weight / total,
            "confidence": self.confidence_weight / total,
            "historical": self.historical_weight / total,
            "constraint": self.constraint_weight / total,
        }

    def requires_fallback(self, confidence: float) -> bool:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                "confidence must be between 0 and 1."
            )

        return (
            self.allow_fallback
            and confidence < self.minimum_confidence
        )
