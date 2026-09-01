from __future__ import annotations

from collections import defaultdict

from .models import (
    OptimizationDecision,
    StrategyOutcome,
    StrategyProfile,
)


class StrategyOptimizer:

    def __init__(self):

        self._outcomes: dict[
            str,
            list[StrategyOutcome],
        ] = defaultdict(list)

    def record(
        self,
        outcome: StrategyOutcome,
    ) -> None:

        if not outcome.strategy.strip():
            raise ValueError(
                "Strategy cannot be empty."
            )

        if not 0 <= outcome.score <= 1:
            raise ValueError(
                "Score must be between 0 and 1."
            )

        self._outcomes[
            outcome.problem_type
        ].append(outcome)

    def profile(
        self,
        problem_type: str = "general",
    ) -> list[StrategyProfile]:

        outcomes = self._outcomes.get(
            problem_type,
            [],
        )

        grouped: dict[
            str,
            list[StrategyOutcome],
        ] = defaultdict(list)

        for outcome in outcomes:
            grouped[
                outcome.strategy
            ].append(outcome)

        profiles = []

        for strategy, records in grouped.items():

            trials = len(records)

            successes = sum(
                1
                for record in records
                if record.success
            )

            total_score = sum(
                record.score
                for record in records
            )

            average_score = (
                total_score / trials
                if trials
                else 0.0
            )

            success_rate = (
                successes / trials
                if trials
                else 0.0
            )

            profiles.append(
                StrategyProfile(
                    strategy=strategy,
                    trials=trials,
                    successes=successes,
                    total_score=round(
                        total_score,
                        4,
                    ),
                    average_score=round(
                        average_score,
                        4,
                    ),
                    success_rate=round(
                        success_rate,
                        4,
                    ),
                )
            )

        profiles.sort(
            key=lambda profile: (
                profile.average_score,
                profile.success_rate,
                profile.trials,
            ),
            reverse=True,
        )

        return profiles

    def choose(
        self,
        problem_type: str = "general",
        available_strategies: list[str] | None = None,
        default_strategy: str = "direct",
    ) -> OptimizationDecision:

        available = (
            available_strategies
            if available_strategies
            else [default_strategy]
        )

        if not available:
            raise ValueError(
                "At least one strategy is required."
            )

        profiles = self.profile(
            problem_type
        )

        known = {
            profile.strategy: profile
            for profile in profiles
        }

        candidates = [
            strategy
            for strategy in available
            if strategy in known
        ]

        if candidates:

            best = max(
                candidates,
                key=lambda strategy: (
                    known[strategy].average_score,
                    known[strategy].success_rate,
                    known[strategy].trials,
                ),
            )

            profile = known[best]

            confidence = min(
                1.0,
                (
                    0.5
                    + (
                        profile.success_rate
                        * 0.3
                    )
                    + (
                        profile.average_score
                        * 0.2
                    )
                ),
            )

            alternatives = [
                strategy
                for strategy in available
                if strategy != best
            ]

            return OptimizationDecision(
                strategy=best,
                confidence=round(
                    confidence,
                    4,
                ),
                reason=(
                    "Selected using observed "
                    "historical strategy performance."
                ),
                alternatives=alternatives,
            )

        return OptimizationDecision(
            strategy=default_strategy
            if default_strategy in available
            else available[0],
            confidence=0.50,
            reason=(
                "No historical performance "
                "was available; using the "
                "configured default strategy."
            ),
            alternatives=[
                strategy
                for strategy in available
                if strategy
                != (
                    default_strategy
                    if default_strategy in available
                    else available[0]
                )
            ],
        )

    def clear(
        self,
        problem_type: str | None = None,
    ) -> None:

        if problem_type is None:
            self._outcomes.clear()
            return

        self._outcomes.pop(
            problem_type,
            None,
        )

    def count(
        self,
        problem_type: str = "general",
    ) -> int:

        return len(
            self._outcomes.get(
                problem_type,
                [],
            )
        )
