from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ControlAction(str, Enum):
    FINALIZE = "finalize"
    RETRY = "retry"
    REPLAN = "replan"
    ESCALATE = "escalate"
    REJECT = "reject"


@dataclass(frozen=True)
class ControlDecision:
    action: ControlAction
    reason: str
    confidence: float
    retryable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
