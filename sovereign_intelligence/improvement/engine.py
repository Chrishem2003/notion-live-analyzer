from __future__ import annotations

from typing import Any

from .models import (
    ImprovementAction,
    ImprovementPlan,
)


class ImprovementEngine:

    def __init__(
        self,
        target_score: float = 0.85,
    ):

        if not 0 <= target_score <= 1:
            raise ValueError(
                "target_score must be between 0 and 1"
            )

        self.target_score = target_score

    def from_evaluation(
        self,
        evaluation: Any,
        objective: str = "",
    ) -> ImprovementPlan:

        if evaluation is None:
            raise ValueError(
                "Evaluation result is required."
            )

        current_score = float(
            getattr(
                evaluation,
                "overall_score",
                0.0,
            )
        )

        actions = []

        dimensions = getattr(
            evaluation,
            "dimensions",
            [],
        )

        for dimension in dimensions:

            score = float(
                getattr(
                    dimension,
                    "score",
                    0.0,
                )
            )

            name = str(
                getattr(
                    dimension,
                    "name",
                    "Unknown",
                )
            )

            reason = str(
                getattr(
                    dimension,
                    "reason",
                    "",
                )
            )

            if score < 0.60:

                priority = "high"

            elif score < 0.80:

                priority = "medium"

            else:

                priority = "low"

            if score < 0.80:

                impact = min(
                    1.0,
                    0.80 - score,
                )

                actions.append(
                    ImprovementAction(
                        title=(
                            "Improve "
                            + name
                        ),
                        description=(
                            "Address the weaknesses "
                            "identified in "
                            + name
                            + ". "
                            + reason
                        ),
                        priority=priority,
                        target_dimension=name,
                        expected_impact=round(
                            impact,
                            4,
                        ),
                    )
                )

        weaknesses = getattr(
            evaluation,
            "weaknesses",
            [],
        )

        for weakness in weaknesses:

            actions.append(
                ImprovementAction(
                    title="Address evaluation weakness",
                    description=str(
                        weakness
                    ),
                    priority="high",
                    expected_impact=0.10,
                )
            )

        actions.sort(
            key=lambda action: (
                {
                    "high": 0,
                    "medium": 1,
                    "low": 2,
                }.get(
                    action.priority,
                    3,
                ),
                -action.expected_impact,
            )
        )

        gap = max(
            0.0,
            self.target_score
            - current_score,
        )

        rationale = (
            "The improvement plan targets "
            f"a score increase of {gap:.4f} "
            "toward the configured quality target."
        )

        return ImprovementPlan(
            objective=objective,
            current_score=current_score,
            target_score=self.target_score,
            actions=actions,
            rationale=rationale,
        )

    def from_quality_gate(
        self,
        gate_result: Any,
        objective: str = "",
    ) -> ImprovementPlan:

        if gate_result is None:
            raise ValueError(
                "Quality gate result is required."
            )

        current_score = float(
            getattr(
                gate_result,
                "score",
                0.0,
            )
        )

        actions = []

        failures = getattr(
            gate_result,
            "failures",
            [],
        )

        recommendations = getattr(
            gate_result,
            "recommendations",
            [],
        )

        for failure in failures:

            actions.append(
                ImprovementAction(
                    title="Resolve quality-gate failure",
                    description=str(
                        failure
                    ),
                    priority="high",
                    expected_impact=0.15,
                )
            )

        for recommendation in recommendations:

            actions.append(
                ImprovementAction(
                    title="Apply quality recommendation",
                    description=str(
                        recommendation
                    ),
                    priority="medium",
                    expected_impact=0.10,
                )
            )

        gap = max(
            0.0,
            self.target_score
            - current_score,
        )

        return ImprovementPlan(
            objective=objective,
            current_score=current_score,
            target_score=self.target_score,
            actions=actions,
            rationale=(
                "Improvement actions were generated "
                "from the quality-gate result."
            ),
        )

    @staticmethod
    def next_strategy(
        current_strategy: str,
    ) -> str:

        transitions = {
            "direct": "decompose",
            "decompose": "verify",
            "verify": "alternative",
            "alternative": "synthesis",
            "synthesis": "review",
        }

        return transitions.get(
            current_strategy,
            "revised",
        )
