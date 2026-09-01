from __future__ import annotations

import re

from .models import (
    EvaluationDimension,
    EvaluationResult,
)


class IntelligenceEvaluator:

    def __init__(
        self,
        passing_score: float = 0.70,
    ):

        if not 0 <= passing_score <= 1:
            raise ValueError(
                "passing_score must be between 0 and 1"
            )

        self.passing_score = passing_score

    def evaluate(
        self,
        answer: str,
        evidence: str = "",
        objective: str = "",
    ) -> EvaluationResult:

        if not isinstance(answer, str):
            raise TypeError(
                "answer must be a string"
            )

        text = answer.strip()

        if not text:

            return EvaluationResult(
                overall_score=0.0,
                passed=False,
                weaknesses=[
                    "The answer is empty."
                ],
                recommendations=[
                    "Generate a substantive answer."
                ],
            )

        dimensions = []

        dimensions.append(
            self._completeness(text)
        )

        dimensions.append(
            self._actionability(text)
        )

        dimensions.append(
            self._uncertainty(text)
        )

        dimensions.append(
            self._evidence_alignment(
                text,
                evidence,
            )
        )

        dimensions.append(
            self._objective_alignment(
                text,
                objective,
            )
        )

        overall = sum(
            dimension.score
            for dimension in dimensions
        ) / len(dimensions)

        strengths = []
        weaknesses = []
        recommendations = []

        for dimension in dimensions:

            if dimension.score >= 0.80:

                strengths.append(
                    dimension.name
                    + ": "
                    + dimension.reason
                )

            elif dimension.score < 0.60:

                weaknesses.append(
                    dimension.name
                    + ": "
                    + dimension.reason
                )

                recommendations.append(
                    "Improve "
                    + dimension.name.lower()
                    + "."
                )

        return EvaluationResult(
            overall_score=round(
                overall,
                4,
            ),
            passed=overall >= self.passing_score,
            dimensions=dimensions,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
        )

    @staticmethod
    def _completeness(
        text: str,
    ) -> EvaluationDimension:

        sentences = [
            item.strip()
            for item in re.split(
                r"[.!?]+",
                text,
            )
            if item.strip()
        ]

        if len(sentences) >= 5:
            score = 1.0
        elif len(sentences) >= 3:
            score = 0.85
        elif len(sentences) >= 2:
            score = 0.70
        else:
            score = 0.45

        return EvaluationDimension(
            name="Completeness",
            score=score,
            reason=(
                f"Answer contains {len(sentences)} "
                "substantive sentence(s)."
            ),
        )

    @staticmethod
    def _actionability(
        text: str,
    ) -> EvaluationDimension:

        action_terms = [
            "step",
            "do",
            "use",
            "create",
            "run",
            "check",
            "implement",
            "configure",
            "install",
            "verify",
            "recommend",
        ]

        matches = sum(
            1
            for term in action_terms
            if re.search(
                rf"\b{re.escape(term)}\b",
                text,
                flags=re.IGNORECASE,
            )
        )

        if matches >= 3:
            score = 1.0
        elif matches >= 2:
            score = 0.85
        elif matches >= 1:
            score = 0.70
        else:
            score = 0.50

        return EvaluationDimension(
            name="Actionability",
            score=score,
            reason=(
                f"Detected {matches} actionable "
                "instruction signal(s)."
            ),
        )

    @staticmethod
    def _uncertainty(
        text: str,
    ) -> EvaluationDimension:

        uncertainty_terms = [
            "may",
            "might",
            "possibly",
            "likely",
            "uncertain",
            "unknown",
            "assuming",
            "depends",
        ]

        absolute_terms = [
            "guaranteed",
            "100%",
            "definitely",
            "always",
            "never",
            "without any doubt",
        ]

        uncertainty_count = sum(
            1
            for term in uncertainty_terms
            if re.search(
                rf"\b{re.escape(term)}\b",
                text,
                flags=re.IGNORECASE,
            )
        )

        absolute_count = sum(
            1
            for term in absolute_terms
            if re.search(
                rf"\b{re.escape(term)}\b",
                text,
                flags=re.IGNORECASE,
            )
        )

        if absolute_count:
            score = 0.40
            reason = (
                "Contains strong certainty claims."
            )
        elif uncertainty_count:
            score = 1.0
            reason = (
                "Explicitly communicates uncertainty "
                "where appropriate."
            )
        else:
            score = 0.75
            reason = (
                "No problematic absolute certainty "
                "claims detected."
            )

        return EvaluationDimension(
            name="Uncertainty Handling",
            score=score,
            reason=reason,
        )

    @staticmethod
    def _evidence_alignment(
        text: str,
        evidence: str,
    ) -> EvaluationDimension:

        if not evidence.strip():

            return EvaluationDimension(
                name="Evidence Alignment",
                score=0.70,
                reason=(
                    "No evidence context was supplied."
                ),
            )

        evidence_terms = set(
            re.findall(
                r"[a-zA-Z0-9_]+",
                evidence.lower(),
            )
        )

        answer_terms = set(
            re.findall(
                r"[a-zA-Z0-9_]+",
                text.lower(),
            )
        )

        if not evidence_terms:

            score = 0.70

        else:

            overlap = len(
                evidence_terms & answer_terms
            )

            score = min(
                1.0,
                0.50
                + (
                    overlap
                    / max(
                        len(evidence_terms),
                        1,
                    )
                ),
            )

        return EvaluationDimension(
            name="Evidence Alignment",
            score=round(score, 4),
            reason=(
                "Measures lexical alignment between "
                "the answer and supplied evidence."
            ),
        )

    @staticmethod
    def _objective_alignment(
        text: str,
        objective: str,
    ) -> EvaluationDimension:

        if not objective.strip():

            return EvaluationDimension(
                name="Objective Alignment",
                score=0.75,
                reason=(
                    "No explicit objective was supplied."
                ),
            )

        objective_terms = set(
            re.findall(
                r"[a-zA-Z0-9_]+",
                objective.lower(),
            )
        )

        answer_terms = set(
            re.findall(
                r"[a-zA-Z0-9_]+",
                text.lower(),
            )
        )

        overlap = len(
            objective_terms & answer_terms
        )

        score = min(
            1.0,
            0.40
            + (
                overlap
                / max(
                    len(objective_terms),
                    1,
                )
            ),
        )

        return EvaluationDimension(
            name="Objective Alignment",
            score=round(score, 4),
            reason=(
                "Measures overlap between the "
                "objective and answer."
            ),
        )
