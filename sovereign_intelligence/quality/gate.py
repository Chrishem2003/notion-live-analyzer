from __future__ import annotations

from typing import Any

from .models import (
    QualityCheck,
    QualityGateResult,
)


class QualityGate:

    def __init__(
        self,
        minimum_score: float = 0.70,
        require_verification: bool = False,
        require_evidence: bool = False,
    ):

        if not 0 <= minimum_score <= 1:
            raise ValueError(
                "minimum_score must be between 0 and 1"
            )

        self.minimum_score = minimum_score
        self.require_verification = require_verification
        self.require_evidence = require_evidence

    def evaluate(
        self,
        evaluation: Any | None = None,
        verification: Any | None = None,
        evidence: str = "",
    ) -> QualityGateResult:

        checks = []
        failures = []
        recommendations = []

        evaluation_score = 0.0

        if evaluation is not None:

            evaluation_score = float(
                getattr(
                    evaluation,
                    "overall_score",
                    0.0,
                )
            )

            evaluation_passed = (
                evaluation_score
                >= self.minimum_score
            )

            checks.append(
                QualityCheck(
                    name="evaluation_score",
                    passed=evaluation_passed,
                    score=evaluation_score,
                    reason=(
                        f"Evaluation score is "
                        f"{evaluation_score:.4f}."
                    ),
                )
            )

            if not evaluation_passed:

                failures.append(
                    "Evaluation score is below "
                    "the configured threshold."
                )

                recommendations.append(
                    "Improve the answer quality "
                    "before accepting the result."
                )

        else:

            checks.append(
                QualityCheck(
                    name="evaluation_score",
                    passed=False,
                    score=0.0,
                    reason="No evaluation result supplied.",
                )
            )

            failures.append(
                "No evaluation result was supplied."
            )

            recommendations.append(
                "Run the intelligence evaluator "
                "before applying the quality gate."
            )

        if self.require_verification:

            verification_passed = (
                verification is not None
                and bool(
                    getattr(
                        verification,
                        "passed",
                        False,
                    )
                )
            )

            verification_score = (
                float(
                    getattr(
                        verification,
                        "confidence",
                        0.0,
                    )
                )
                if verification is not None
                else 0.0
            )

            checks.append(
                QualityCheck(
                    name="verification",
                    passed=verification_passed,
                    score=verification_score,
                    reason=(
                        "Verification passed."
                        if verification_passed
                        else
                        "Verification did not pass."
                    ),
                )
            )

            if not verification_passed:

                failures.append(
                    "Verification requirement failed."
                )

                recommendations.append(
                    "Review verification issues "
                    "before accepting the result."
                )

        if self.require_evidence:

            evidence_present = bool(
                evidence.strip()
            )

            evidence_score = (
                1.0
                if evidence_present
                else 0.0
            )

            checks.append(
                QualityCheck(
                    name="evidence",
                    passed=evidence_present,
                    score=evidence_score,
                    reason=(
                        "Evidence context is available."
                        if evidence_present
                        else
                        "No evidence context is available."
                    ),
                )
            )

            if not evidence_present:

                failures.append(
                    "Evidence requirement failed."
                )

                recommendations.append(
                    "Retrieve supporting evidence "
                    "before accepting the result."
                )

        score_values = [
            check.score
            for check in checks
        ]

        score = (
            sum(score_values)
            / len(score_values)
            if score_values
            else 0.0
        )

        passed = (
            score >= self.minimum_score
            and not failures
        )

        return QualityGateResult(
            passed=passed,
            score=round(score, 4),
            checks=checks,
            failures=failures,
            recommendations=recommendations,
            metadata={
                "minimum_score": self.minimum_score,
                "require_verification":
                    self.require_verification,
                "require_evidence":
                    self.require_evidence,
            },
        )
