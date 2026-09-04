from __future__ import annotations

from typing import Any

from .control_models import ControlAction, ControlDecision


class DecisionControlEngine:
    """
    Stage 48 control layer.

    Converts an evaluated decision into an explicit next action
    without replacing the existing DecisionEngine or Evaluator.
    """

    def __init__(
        self,
        minimum_confidence: float = 0.70,
        retry_limit: int = 2,
    ) -> None:
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError(
                "minimum_confidence must be between 0 and 1"
            )

        if retry_limit < 0:
            raise ValueError(
                "retry_limit must be >= 0"
            )

        self.minimum_confidence = minimum_confidence
        self.retry_limit = retry_limit

    def decide(
        self,
        decision: Any,
        evaluation: Any,
        retry_count: int = 0,
    ) -> ControlDecision:
        """
        Determine the next system action.

        The method intentionally accepts protocol-like objects so it
        remains compatible with the existing DecisionResult and
        EvaluationResult implementations.
        """

        decision_confidence = self._bounded(
            getattr(decision, "confidence", 0.0)
        )

        evaluation_score = self._bounded(
            getattr(evaluation, "overall_score", 0.0)
        )

        evaluation_passed = bool(
            getattr(evaluation, "passed", False)
        )

        consensus = bool(
            getattr(decision, "consensus", False)
        )

        decision_text = str(
            getattr(decision, "decision", "")
        ).strip()

        conflicts = list(
            getattr(decision, "conflicts", []) or []
        )

        recommendations = list(
            getattr(evaluation, "recommendations", []) or []
        )

        weaknesses = list(
            getattr(evaluation, "weaknesses", []) or []
        )

        if not decision_text:
            return ControlDecision(
                action=ControlAction.REJECT,
                reason="No usable decision was produced.",
                confidence=0.0,
                retryable=False,
                metadata={
                    "evaluation_score": evaluation_score,
                    "decision_confidence": decision_confidence,
                },
            )

        if (
            evaluation_passed
            and decision_confidence >= self.minimum_confidence
            and consensus
        ):
            return ControlDecision(
                action=ControlAction.FINALIZE,
                reason=(
                    "Decision passed evaluation with sufficient "
                    "confidence and specialist consensus."
                ),
                confidence=self._combined_confidence(
                    decision_confidence,
                    evaluation_score,
                ),
                retryable=False,
                metadata={
                    "evaluation_score": evaluation_score,
                    "decision_confidence": decision_confidence,
                    "consensus": consensus,
                    "conflicts": len(conflicts),
                },
            )

        if retry_count >= self.retry_limit:
            if conflicts:
                return ControlDecision(
                    action=ControlAction.ESCALATE,
                    reason=(
                        "Retry limit reached while specialist "
                        "conflicts remain unresolved."
                    ),
                    confidence=self._combined_confidence(
                        decision_confidence,
                        evaluation_score,
                    ),
                    retryable=False,
                    metadata={
                        "retry_count": retry_count,
                        "retry_limit": self.retry_limit,
                        "conflicts": len(conflicts),
                    },
                )

            return ControlDecision(
                action=ControlAction.REJECT,
                reason=(
                    "Retry limit reached without producing a "
                    "passing decision."
                ),
                confidence=self._combined_confidence(
                    decision_confidence,
                    evaluation_score,
                ),
                retryable=False,
                metadata={
                    "retry_count": retry_count,
                    "retry_limit": self.retry_limit,
                    "weaknesses": weaknesses,
                },
            )

        if conflicts and not consensus:
            return ControlDecision(
                action=ControlAction.ESCALATE,
                reason=(
                    "Specialist findings remain in conflict and "
                    "do not meet the consensus threshold."
                ),
                confidence=decision_confidence,
                retryable=False,
                metadata={
                    "conflicts": conflicts,
                    "recommendations": recommendations,
                },
            )

        objective_problem = any(
            "objective" in str(item).lower()
            for item in weaknesses + recommendations
        )

        if objective_problem:
            return ControlDecision(
                action=ControlAction.REPLAN,
                reason=(
                    "Evaluation indicates insufficient alignment "
                    "with the requested objective."
                ),
                confidence=evaluation_score,
                retryable=True,
                metadata={
                    "weaknesses": weaknesses,
                    "recommendations": recommendations,
                },
            )

        if not evaluation_passed:
            return ControlDecision(
                action=ControlAction.RETRY,
                reason=(
                    "Evaluation did not pass; another reasoning "
                    "or execution attempt is warranted."
                ),
                confidence=evaluation_score,
                retryable=True,
                metadata={
                    "retry_count": retry_count,
                    "recommendations": recommendations,
                    "weaknesses": weaknesses,
                },
            )

        if decision_confidence < self.minimum_confidence:
            return ControlDecision(
                action=ControlAction.RETRY,
                reason=(
                    "Decision confidence is below the configured "
                    "minimum threshold."
                ),
                confidence=decision_confidence,
                retryable=True,
                metadata={
                    "minimum_confidence": self.minimum_confidence,
                    "retry_count": retry_count,
                },
            )

        return ControlDecision(
            action=ControlAction.FINALIZE,
            reason=(
                "Decision is acceptable under the configured "
                "control policy."
            ),
            confidence=self._combined_confidence(
                decision_confidence,
                evaluation_score,
            ),
            retryable=False,
            metadata={
                "evaluation_score": evaluation_score,
                "decision_confidence": decision_confidence,
                "consensus": consensus,
            },
        )

    @staticmethod
    def _bounded(value: Any) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0

        return max(0.0, min(1.0, value))

    @staticmethod
    def _combined_confidence(
        decision_confidence: float,
        evaluation_score: float,
    ) -> float:
        return round(
            (decision_confidence + evaluation_score) / 2.0,
            4,
        )
