from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderCandidate:

    name: str
    model: str
    priority: int = 100
    capabilities: set[str] = field(
        default_factory=set
    )
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class RoutingDecision:

    provider: str
    model: str
    reason: str
    attempted: list[str] = field(
        default_factory=list
    )


@dataclass
class ProviderAttempt:

    provider: str
    model: str
    success: bool
    error: str | None = None
    response: Any = None


@dataclass
class RoutingResult:

    decision: RoutingDecision
    attempts: list[ProviderAttempt] = field(
        default_factory=list
    )
