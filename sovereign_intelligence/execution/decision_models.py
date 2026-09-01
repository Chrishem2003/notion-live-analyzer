from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentVote:
    agent: str
    position: str
    confidence: float
    evidence: str = ""


@dataclass
class DecisionResult:
    decision: str
    confidence: float
    consensus: bool
    votes: list[AgentVote] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    rationale: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
