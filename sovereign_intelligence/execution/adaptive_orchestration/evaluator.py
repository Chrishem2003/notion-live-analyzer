from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass
class IntermediateResultAssessment:
    """Quality assessment of an intermediate execution result."""

    score: float
    completeness: float
    confidence: float

    useful: bool
    needs_reassessment: bool

    result_length: int
    matched_objective_terms: list[str] = field(
        default_factory=list
    )

    evidence_signals: list[str] = field(
        default_factory=list
    )

    uncertainty_signals: list[str] = field(
        default_factory=list
    )

    reason: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class IntermediateResultEvaluator:
    """Deterministically evaluates intermediate result quality."""

    EVIDENCE_TERMS = {
        "because",
        "evidence",
        "source",
        "verified",
        "verification",
        "test",
        "tested",
        "result",
        "observed",
        "confirmed",
        "documentation",
        "according",
    }

    UNCERTAINTY_TERMS = {
        "maybe",
        "perhaps",
        "possibly",
        "uncertain",
        "unknown",
        "assume",
        "assumption",
        "might",
        "could be",
    }

    def __init__(
        self,
        *,
        minimum_score: float = 0.55,
        minimum_completeness: float = 0.50,
        minimum_confidence: float = 0.50,
    ):
        for name, value in {
            "minimum_score": minimum_score,
            "minimum_completeness": minimum_completeness,
            "minimum_confidence": minimum_confidence,
        }.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1."
                )

        self.minimum_score = minimum_score
        self.minimum_completeness = (
            minimum_completeness
        )
        self.minimum_confidence = minimum_confidence

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(
            re.findall(
                r"[a-zA-Z0-9_]+",
                text.lower(),
            )
        )

    @classmethod
    def _objective_terms(
        cls,
        objective: str,
    ) -> list[str]:
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "of",
            "in",
            "on",
            "for",
            "with",
            "is",
            "are",
            "be",
            "this",
            "that",
            "how",
            "what",
            "why",
        }

        tokens = cls._tokens(objective)

        return sorted(
            token
            for token in tokens
            if len(token) >= 3
            and token not in stop_words
        )

    def evaluate(
        self,
        result: str,
        *,
        objective: str = "",
        expected_terms: list[str] | None = None,
    ) -> IntermediateResultAssessment:
        if result is None:
            raise ValueError(
                "result cannot be None."
            )

        if objective is None:
            raise ValueError(
                "objective cannot be None."
            )

        result = str(result).strip()
        objective = str(objective).strip()

        tokens = self._tokens(result)

        if expected_terms is not None:
            objective_terms = sorted(
                {
                    str(term).strip().lower()
                    for term in expected_terms
                    if str(term).strip()
                }
            )
        else:
            objective_terms = self._objective_terms(
                objective
            )

        matched_terms = [
            term
            for term in objective_terms
            if term in tokens
        ]

        if objective_terms:
            completeness = (
                len(matched_terms)
                / len(objective_terms)
            )
        else:
            completeness = (
                1.0 if result else 0.0
            )

        evidence_signals = sorted(
            term
            for term in self.EVIDENCE_TERMS
            if term in tokens
        )

        uncertainty_signals = sorted(
            term
            for term in self.UNCERTAINTY_TERMS
            if term in tokens
        )

        length_score = min(
            1.0,
            len(result) / 500.0,
        )

        evidence_score = min(
            1.0,
            len(evidence_signals) / 3.0,
        )

        uncertainty_penalty = min(
            0.40,
            len(uncertainty_signals) * 0.08,
        )

        score = (
            completeness * 0.45
            + length_score * 0.20
            + evidence_score * 0.20
            + (1.0 if result else 0.0) * 0.15
            - uncertainty_penalty
        )

        score = max(
            0.0,
            min(1.0, score),
        )

        confidence = (
            completeness * 0.50
            + evidence_score * 0.30
            + (
                1.0
                - min(
                    1.0,
                    len(uncertainty_signals) / 5.0,
                )
            )
            * 0.20
        )

        confidence = max(
            0.0,
            min(1.0, confidence),
        )

        useful = (
            score >= self.minimum_score
            and completeness
            >= self.minimum_completeness
        )

        needs_reassessment = (
            not useful
            or confidence
            < self.minimum_confidence
        )

        if useful:
            reason = (
                "Intermediate result meets the configured "
                "quality and completeness thresholds."
            )
        else:
            reasons = []

            if score < self.minimum_score:
                reasons.append(
                    "quality score below threshold"
                )

            if completeness < self.minimum_completeness:
                reasons.append(
                    "result completeness below threshold"
                )

            if confidence < self.minimum_confidence:
                reasons.append(
                    "confidence below threshold"
                )

            reason = (
                "Intermediate result requires reassessment: "
                + ", ".join(reasons)
                + "."
            )

        return IntermediateResultAssessment(
            score=round(score, 4),
            completeness=round(completeness, 4),
            confidence=round(confidence, 4),
            useful=useful,
            needs_reassessment=needs_reassessment,
            result_length=len(result),
            matched_objective_terms=matched_terms,
            evidence_signals=evidence_signals,
            uncertainty_signals=uncertainty_signals,
            reason=reason,
            metadata={
                "minimum_score": self.minimum_score,
                "minimum_completeness": (
                    self.minimum_completeness
                ),
                "minimum_confidence": (
                    self.minimum_confidence
                ),
                "objective_terms": objective_terms,
            },
        )
