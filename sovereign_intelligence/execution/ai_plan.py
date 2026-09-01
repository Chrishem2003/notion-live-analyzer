from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIActionProposal:

    action: str
    target: str
    arguments: dict[str, Any] = field(
        default_factory=dict
    )

    rationale: str = ""


@dataclass
class AIPlanProposal:

    objective: str

    actions: list[AIActionProposal] = field(
        default_factory=list
    )

    final_response: str = ""

    confidence: float = 0.0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )
