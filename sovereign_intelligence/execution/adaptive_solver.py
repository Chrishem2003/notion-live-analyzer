from typing import Any, Callable
from .adaptive import AdaptiveResult, RecoveryAttempt

class AdaptiveSolver:

    def __init__(self, max_attempts: int = 3):
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")
        self.max_attempts = max_attempts

    def solve(
        self,
        operation: Callable[[str], Any],
        problem: str,
    ) -> AdaptiveResult:

        attempts = []
        strategies = ["direct", "reconsider", "alternative"]
        last_error = ""

        for index in range(self.max_attempts):

            strategy = strategies[min(index, len(strategies) - 1)]

            attempt = RecoveryAttempt(
                attempt=index + 1,
                strategy=strategy,
                reason=(
                    "Initial solution attempt."
                    if index == 0
                    else
                    "Previous attempt failed; trying another strategy."
                ),
            )

            try:
                result = operation(
                    self._prepare_prompt(problem, strategy)
                )

                answer = self._extract_answer(result)

                if answer.strip():
                    attempt.status = "success"
                    attempt.result = result
                    attempts.append(attempt)

                    return AdaptiveResult(
                        success=True,
                        answer=answer,
                        attempts=attempts,
                        final_reason="Usable solution produced.",
                    )

                attempt.status = "empty"
                last_error = "Empty solution."

            except Exception as exc:
                attempt.status = "failed"
                attempt.result = str(exc)
                last_error = str(exc)

            attempts.append(attempt)

        return AdaptiveResult(
            success=False,
            answer="",
            attempts=attempts,
            final_reason=last_error or "All attempts failed.",
        )

    @staticmethod
    def _prepare_prompt(problem, strategy):

        if strategy == "direct":
            return problem

        if strategy == "reconsider":
            return (
                "Reconsider the problem from first principles.\n\n"
                + problem
            )

        return (
            "Use an alternative solution strategy.\n"
            "Check assumptions carefully.\n\n"
            + problem
        )

    @staticmethod
    def _extract_answer(result):

        if result is None:
            return ""

        if isinstance(result, str):
            return result

        if hasattr(result, "text"):
            return str(result.text)

        if hasattr(result, "answer"):
            return str(result.answer)

        return str(result)
