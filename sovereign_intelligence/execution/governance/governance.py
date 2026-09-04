from __future__ import annotations

from typing import Any

from ..control_models import ControlAction, ControlDecision
from .history import DecisionHistory
from .models import DecisionRecord, GovernanceAssessment


class DecisionGovernanceEngine:
    """
    Stage 49 governance layer.

    It observes Stage 48 ControlDecision objects and evaluates
    consistency across decision history.

    It does NOT replace DecisionControlEngine.
    """

    def __init__(
        self,
        history: DecisionHistory | None = None,
        minimum_consistency: float = 0.60,
    ) -> None:
        if not 0.0 <= minimum_consistency <= 1.0:
            raise ValueError(
                "minimum_consistency must be between 0 and 1"
            )

        self.history = history or DecisionHistory()
        self.minimum_consistency = minimum_consistency

    def record(
        self,
        control_decision: ControlDecision,
        *,
        decision_id: str,
        decision_confidence: float = 0.0,
        evaluation_score: float = 0.0,
        consensus: bool = False,
        retry_count: int = 0,
    ) -> DecisionRecord:
        if not isinstance(control_decision, ControlDecision):
            raise TypeError(
                "control_decision must be a ControlDecision"
            )

        if not decision_id.strip():
            raise ValueError("decision_id must not be empty")

        if retry_count < 0:
            raise ValueError("retry_count must be >= 0")

        record = DecisionRecord(
            decision_id=decision_id,
            action=control_decision.action,
            reason=control_decision.reason,
            confidence=self._bounded(control_decision.confidence),
            retryable=control_decision.retryable,
            decision_confidence=self._bounded(decision_confidence),
            evaluation_score=self._bounded(evaluation_score),
            consensus=bool(consensus),
            retry_count=retry_count,
            metadata=dict(control_decision.metadata),
        )

        self.history.append(record)

        return record

    def assess(
        self,
        record: DecisionRecord | None = None,
    ) -> GovernanceAssessment:
        target = record or self.history.latest()

        if target is None:
            return GovernanceAssessment(
                accepted=False,
                consistency_score=0.0,
                confidence_stability=0.0,
                repeated_action=False,
                escalation_detected=False,
                reason="No decision record is available.",
            )

        previous = [
            item
            for item in self.history.all()
            if item.decision_id != target.decision_id
        ]

        if not previous:
            return GovernanceAssessment(
                accepted=True,
                consistency_score=1.0,
                confidence_stability=1.0,
                repeated_action=False,
                escalation_detected=(
                    target.action is ControlAction.ESCALATE
                ),
                reason=(
                    "First recorded decision has no prior history "
                    "against which to compare."
                ),
            )

        same_action = sum(
            item.action is target.action
            for item in previous
        )

        consistency_score = same_action / len(previous)

        previous_confidences = [
            item.confidence
            for item in previous
        ]

        average_previous = (
            sum(previous_confidences)
            / len(previous_confidences)
        )

        confidence_stability = max(
            0.0,
            1.0 - abs(
                target.confidence - average_previous
            ),
        )

        repeated_action = same_action > 0

        escalation_detected = (
            target.action is ControlAction.ESCALATE
            or any(
                item.action is ControlAction.ESCALATE
                for item in previous
            )
        )

        accepted = (
            consistency_score >= self.minimum_consistency
            or target.action in {
                ControlAction.FINALIZE,
                ControlAction.REPLAN,
            }
        )

        if accepted:
            reason = (
                "Decision is consistent with governance history "
                "under the configured policy."
            )
        else:
            reason = (
                "Decision differs materially from prior control "
                "actions and requires governance attention."
            )

        return GovernanceAssessment(
            accepted=accepted,
            consistency_score=round(
                consistency_score,
                4,
            ),
            confidence_stability=round(
                confidence_stability,
                4,
            ),
            repeated_action=repeated_action,
            escalation_detected=escalation_detected,
            reason=reason,
            metadata={
                "history_size": len(previous),
                "same_action_count": same_action,
                "target_action": target.action.value,
            },
        )

    @staticmethod
    def _bounded(value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0

        return max(
            0.0,
            min(1.0, numeric),
        )
