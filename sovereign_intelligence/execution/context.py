from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProblemContext:

    problem: str

    memory: list[Any] = field(
        default_factory=list
    )

    knowledge: list[Any] = field(
        default_factory=list
    )

    plan: list[Any] = field(
        default_factory=list
    )

    observations: list[Any] = field(
        default_factory=list
    )

    tool_results: list[Any] = field(
        default_factory=list
    )

    verification: list[Any] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def add_observation(self, value):
        self.observations.append(value)

    def add_tool_result(self, value):
        self.tool_results.append(value)

    def add_verification(self, value):
        self.verification.append(value)

    def snapshot(self):

        return {
            "problem": self.problem,
            "memory": list(self.memory),
            "knowledge": list(self.knowledge),
            "plan": list(self.plan),
            "observations": list(self.observations),
            "tool_results": list(self.tool_results),
            "verification": list(self.verification),
            "metadata": dict(self.metadata),
        }
