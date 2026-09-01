from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdaptiveAttempt:
    number: int
    strategy: str
    success: bool
    confidence: float
    answer: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdaptiveResult:
    success: bool
    answer: str
    confidence: float
    attempts: list[AdaptiveAttempt] = field(default_factory=list)
    final_strategy: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
