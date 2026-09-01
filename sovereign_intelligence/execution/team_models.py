from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContribution:
    agent: str
    role: str
    success: bool
    answer: str = ""
    confidence: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamResult:
    objective: str
    contributions: list[AgentContribution] = field(default_factory=list)
    consensus: str = ""
    confidence: float = 0.0
    disagreements: list[str] = field(default_factory=list)
    successful_agents: int = 0
    failed_agents: int = 0

    @property
    def success(self) -> bool:
        return bool(self.consensus.strip()) and self.successful_agents > 0
