from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..control_models import ControlDecision
from ..decision_models import DecisionResult
from ..decision_control import DecisionControlEngine

from .governance import DecisionGovernanceEngine
from .models import DecisionRecord, GovernanceAssessment


@dataclass(frozen=True)
class GovernedDecision:
    """
    Complete Stage 50 governance result.

    This object preserves the relationship between the original
    decision, Stage 48 control output, Stage 49 governance record,
    and governance assessment.
    """

    decision_id: str
    decision: DecisionResult
    control: ControlDecision
    record: DecisionRecord
    assessment: GovernanceAssessment


class GovernedDecisionPipeline:
    """
    Stage 50 orchestration boundary for decision governance.

    This class composes existing Stage 48 and Stage 49 components.
    It does not replace or modify either component.
    """

    def __init__(
        self,
        control_engine: DecisionControlEngine | None = None,
        governance_engine: DecisionGovernanceEngine | None = None,
    ) -> None:
        self.control_engine = (
            control_engine
            or DecisionControlEngine()
        )

        self.governance_engine = (
            governance_engine
            or DecisionGovernanceEngine()
        )

    def run(
        self,
        decision: DecisionResult,
        evaluation: Any,
        *,
        decision_id: str,
        retry_count: int = 0,
        decision_confidence: float | None = None,
        evaluation_score: float | None = None,
        consensus: bool | None = None,
    ) -> GovernedDecision:
        """
        Execute the complete Stage 48 -> Stage 49 governance path.

        The original DecisionResult is treated as immutable input by
        this pipeline. The existing DecisionControlEngine remains the
        authority for determining the control action.
        """

        if not isinstance(
            decision,
            DecisionResult,
        ):
            raise TypeError(
                "decision must be a DecisionResult"
            )

        if not decision_id.strip():
            raise ValueError(
                "decision_id must not be empty"
            )

        if retry_count < 0:
            raise ValueError(
                "retry_count must be >= 0"
            )

        control = self.control_engine.decide(
            decision,
            evaluation,
            retry_count=retry_count,
        )

        resolved_decision_confidence = (
            decision.confidence
            if decision_confidence is None
            else decision_confidence
        )

        resolved_evaluation_score = (
            self._resolve_evaluation_score(
                evaluation
            )
            if evaluation_score is None
            else evaluation_score
        )

        resolved_consensus = (
            decision.consensus
            if consensus is None
            else consensus
        )

        record = self.governance_engine.record(
            control,
            decision_id=decision_id,
            decision_confidence=(
                resolved_decision_confidence
            ),
            evaluation_score=(
                resolved_evaluation_score
            ),
            consensus=resolved_consensus,
            retry_count=retry_count,
        )

        assessment = self.governance_engine.assess(
            record
        )

        return GovernedDecision(
            decision_id=decision_id,
            decision=decision,
            control=control,
            record=record,
            assessment=assessment,
        )

    @staticmethod
    def _resolve_evaluation_score(
        evaluation: Any,
    ) -> float:
        """
        Resolve a governance score from a supplied evaluation.

        Stage 50 does not invent a score for Stage 47's
        ResearchEvaluationEngine. If the evaluation object exposes
        an explicit overall_score, that value is used. Otherwise
        zero is passed to governance.
        """

        value = getattr(
            evaluation,
            "overall_score",
            0.0,
        )

        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
