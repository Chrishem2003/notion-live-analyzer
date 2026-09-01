from typing import Callable

from .models import AdaptiveAttempt, AdaptiveResult


class AdaptiveEngine:

    def __init__(
        self,
        max_attempts: int = 3,
        minimum_confidence: float = 0.70,
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        if not 0 <= minimum_confidence <= 1:
            raise ValueError(
                "minimum_confidence must be between 0 and 1"
            )

        self.max_attempts = max_attempts
        self.minimum_confidence = minimum_confidence

    def run(
        self,
        problem: str,
        solver: Callable,
        strategy: str = "direct",
    ) -> AdaptiveResult:

        if not problem.strip():
            raise ValueError("Problem cannot be empty")

        attempts = []
        current_strategy = strategy
        last_answer = ""
        last_confidence = 0.0

        for number in range(1, self.max_attempts + 1):

            try:
                result = solver(
                    problem,
                    number,
                    current_strategy,
                )

                if not isinstance(result, dict):
                    raise TypeError(
                        "Solver must return a dictionary"
                    )

                answer = str(result.get("answer", ""))
                confidence = float(
                    result.get("confidence", 0.0)
                )
                success = bool(
                    result.get("success", False)
                )

                attempt = AdaptiveAttempt(
                    number=number,
                    strategy=current_strategy,
                    success=success,
                    confidence=confidence,
                    answer=answer,
                    error=(
                        str(result["error"])
                        if result.get("error") is not None
                        else None
                    ),
                    metadata=result.get("metadata", {}),
                )

                attempts.append(attempt)

                last_answer = answer
                last_confidence = confidence

                if (
                    success
                    and confidence >= self.minimum_confidence
                ):
                    return AdaptiveResult(
                        success=True,
                        answer=answer,
                        confidence=confidence,
                        attempts=attempts,
                        final_strategy=current_strategy,
                    )

                current_strategy = self.revise(
                    current_strategy
                )

            except Exception as exc:

                attempts.append(
                    AdaptiveAttempt(
                        number=number,
                        strategy=current_strategy,
                        success=False,
                        confidence=0.0,
                        error=str(exc),
                    )
                )

                current_strategy = self.revise(
                    current_strategy
                )

        return AdaptiveResult(
            success=False,
            answer=last_answer,
            confidence=last_confidence,
            attempts=attempts,
            final_strategy=current_strategy,
        )

    @staticmethod
    def revise(strategy: str) -> str:

        transitions = {
            "direct": "decompose",
            "decompose": "verify",
            "verify": "alternative",
            "alternative": "synthesis",
        }

        return transitions.get(
            strategy,
            "revised",
        )
