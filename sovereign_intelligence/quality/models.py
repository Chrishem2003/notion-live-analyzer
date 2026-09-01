from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityCheck:

    name: str
    passed: bool
    score: float
    reason: str = ""


@dataclass
class QualityGateResult:

    passed: bool
    score: float

    checks: list[QualityCheck] = field(
        default_factory=list
    )

    failures: list[str] = field(
        default_factory=list
    )

    recommendations: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )
