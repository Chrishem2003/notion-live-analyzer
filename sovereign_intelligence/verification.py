from __future__ import annotations

import re

from .models import VerificationResult


class Verifier:

    def evaluate(
        self,
        answer: str,
    ) -> VerificationResult:

        issues = []
        recommendations = []

        if not answer.strip():
            return VerificationResult(
                passed=False,
                confidence=0.0,
                issues=["The AI returned an empty answer."],
            )

        suspicious = [
            r"\bguaranteed\b",
            r"\b100%\b",
            r"\bdefinitely\b",
            r"\bwithout any doubt\b",
        ]

        for pattern in suspicious:

            if re.search(
                pattern,
                answer,
                flags=re.IGNORECASE,
            ):
                issues.append(
                    "Answer contains an unusually strong certainty claim."
                )

        if issues:

            recommendations.append(
                "Rephrase absolute claims unless independently verified."
            )

        confidence = 0.95 if not issues else 0.70

        return VerificationResult(
            passed=True,
            confidence=confidence,
            issues=issues,
            recommendations=recommendations,
        )