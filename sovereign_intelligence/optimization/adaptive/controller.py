from __future__ import annotations

from ..models import (
    OptimizationDecision,
    StrategyOutcome,
)

from ..optimizer import StrategyOptimizer
from ..persistent import PersistentStrategyStore


class PersistentAdaptiveController:

    def __init__(
        self,
        store: PersistentStrategyStore,
        optimizer: StrategyOptimizer | None = None,
    ):
        self.store = store
        self.optimizer = (
            optimizer
            or StrategyOptimizer()
        )

        self._load_history()

    def _load_history(self) -> None:

        import sqlite3

        with self.store._connect() as db:

            rows = db.execute(
                """
                SELECT DISTINCT problem_type
                FROM strategy_outcomes
                """
            ).fetchall()

        for row in rows:

            problem_type = str(row[0])

            outcomes = self.store.recent(
                problem_type=problem_type,
                limit=10000,
            )

            for outcome in outcomes:

                self.optimizer.record(
                    outcome
                )

    def choose(
        self,
        problem_type: str = "general",
        strategies: list[str] | None = None,
        default_strategy: str = "direct",
    ) -> OptimizationDecision:

        return self.optimizer.choose(
            problem_type=problem_type,
            available_strategies=strategies,
            default_strategy=default_strategy,
        )

    def record(
        self,
        outcome: StrategyOutcome,
    ) -> None:

        self.store.record(
            outcome
        )

        self.optimizer.record(
            outcome
        )

    def history_count(
        self,
        problem_type: str = "general",
    ) -> int:

        return self.store.count(
            problem_type
        )
