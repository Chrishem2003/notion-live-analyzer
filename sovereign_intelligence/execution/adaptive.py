from dataclasses import dataclass, field
from typing import Any

@dataclass
class RecoveryAttempt:
    attempt: int
    strategy: str
    reason: str
    status: str = "pending"
    result: Any = None

@dataclass
class AdaptiveResult:
    success: bool
    answer: str = ""
    attempts: list = field(default_factory=list)
    final_reason: str = ""
