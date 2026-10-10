from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .errors import ProviderErrorCategory, ProviderErrorClassifier


@dataclass(frozen=True)
class RetryPolicyConfig:
    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 30.0
    jitter_ratio: float = 0.25


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    attempt: int
    delay_seconds: float
    category: ProviderErrorCategory
    reason: str


class ProviderRetryPolicy:
    """Deterministic retry policy with exponential backoff and jitter."""

    def __init__(
        self,
        config: RetryPolicyConfig | None = None,
        rng: Random | None = None,
    ) -> None:
        self.config = config or RetryPolicyConfig()

        if self.config.max_attempts <= 0:
            raise ValueError(
                "max_attempts must be greater than zero"
            )

        if self.config.base_delay_seconds < 0:
            raise ValueError(
                "base_delay_seconds must not be negative"
            )

        if self.config.max_delay_seconds < 0:
            raise ValueError(
                "max_delay_seconds must not be negative"
            )

        if self.config.jitter_ratio < 0:
            raise ValueError(
                "jitter_ratio must not be negative"
            )

        if (
            self.config.max_delay_seconds
            < self.config.base_delay_seconds
        ):
            raise ValueError(
                "max_delay_seconds must be greater than "
                "or equal to base_delay_seconds"
            )

        self._rng = rng or Random()

    def decide(
        self,
        error: BaseException | str,
        attempt: int,
    ) -> RetryDecision:
        if attempt <= 0:
            raise ValueError(
                "attempt must be greater than zero"
            )

        classification = ProviderErrorClassifier.classify(
            error
        )

        if not classification.retryable:
            return RetryDecision(
                retry=False,
                attempt=attempt,
                delay_seconds=0.0,
                category=classification.category,
                reason=classification.reason,
            )

        if attempt >= self.config.max_attempts:
            return RetryDecision(
                retry=False,
                attempt=attempt,
                delay_seconds=0.0,
                category=classification.category,
                reason=(
                    "Retry limit reached: "
                    f"{classification.reason}"
                ),
            )

        delay = self._calculate_delay(attempt)

        return RetryDecision(
            retry=True,
            attempt=attempt,
            delay_seconds=delay,
            category=classification.category,
            reason=classification.reason,
        )

    def _calculate_delay(self, attempt: int) -> float:
        exponential = (
            self.config.base_delay_seconds
            * (2 ** max(0, attempt - 1))
        )

        bounded = min(
            exponential,
            self.config.max_delay_seconds,
        )

        if bounded <= 0:
            return 0.0

        jitter = (
            self._rng.uniform(
                -self.config.jitter_ratio,
                self.config.jitter_ratio,
            )
            * bounded
        )

        return max(
            0.0,
            min(
                bounded + jitter,
                self.config.max_delay_seconds,
            ),
        )
