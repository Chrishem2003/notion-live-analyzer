from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..control_models import ControlAction


@dataclass(frozen=True)
class DecisionRecord:
    """
    Immutable governance record for one control decision.

    This layer records what Stage 48 decided without replacing
    DecisionControlEngine or changing its decision semantics.
    """

    decision_id: str
    action: ControlAction
    reason: str
    confidence: float
    retryable: bool
    decision_confidence: float
    evaluation_score: float
    consensus: bool
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernanceAssessment:
    """
    Assessment of a decision against its recorded history.
    """

    accepted: bool
    consistency_score: float
    confidence_stability: float
    repeated_action: bool
    escalation_detected: bool
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)
