from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import (
    StrategyOutcome,
    StrategyProfile,
)


class PersistentStrategyStore:

    def __init__(self, path: str):

        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize()

    def _connect(self):
        return sqlite3.connect(
            self.path
        )

    def _initialize(self):

        with self._connect() as db:

            db.execute(
                """
                CREATE TABLE IF NOT EXISTS
                strategy_outcomes (
                    id INTEGER PRIMARY KEY
                    AUTOINCREMENT,
                    strategy TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    score REAL NOT NULL,
                    attempts INTEGER NOT NULL,
                    problem_type TEXT NOT NULL,
                    metadata TEXT
                )
                """
            )

    def record(
        self,
        outcome: StrategyOutcome,
    ) -> None:

        import json

        with self._connect() as db:

            db.execute(
                """
                INSERT INTO strategy_outcomes
                (
                    strategy,
                    success,
                    score,
                    attempts,
                    problem_type,
                    metadata
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    outcome.strategy,
                    int(outcome.success),
                    outcome.score,
                    outcome.attempts,
                    outcome.problem_type,
                    json.dumps(
                        outcome.metadata
                    ),
                ),
            )

    def recent(
        self,
        problem_type: str = "general",
        limit: int = 100,
    ) -> list[StrategyOutcome]:

        import json

        with self._connect() as db:

            rows = db.execute(
                """
                SELECT
                    strategy,
                    success,
                    score,
                    attempts,
                    problem_type,
                    metadata
                FROM strategy_outcomes
                WHERE problem_type = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    problem_type,
                    limit,
                ),
            ).fetchall()

        return [
            StrategyOutcome(
                strategy=row[0],
                success=bool(row[1]),
                score=float(row[2]),
                attempts=int(row[3]),
                problem_type=row[4],
                metadata=json.loads(
                    row[5] or "{}"
                ),
            )
            for row in rows
        ]

    def profiles(
        self,
        problem_type: str = "general",
    ) -> list[StrategyProfile]:

        outcomes = self.recent(
            problem_type=problem_type,
            limit=10000,
        )

        grouped: dict[
            str,
            list[StrategyOutcome],
        ] = {}

        for outcome in outcomes:

            grouped.setdefault(
                outcome.strategy,
                [],
            ).append(outcome)

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

    def count(
        self,
        problem_type: str = "general",
    ) -> int:

        with self._connect() as db:

            row = db.execute(
                """
                SELECT COUNT(*)
                FROM strategy_outcomes
                WHERE problem_type = ?
                """,
                (problem_type,),
            ).fetchone()

        return int(row[0])

    def clear(
        self,
        problem_type: str | None = None,
    ) -> None:

        with self._connect() as db:

            if problem_type is None:

                db.execute(
                    "DELETE FROM strategy_outcomes"
                )

            else:

                db.execute(
                    """
                    DELETE FROM strategy_outcomes
                    WHERE problem_type = ?
                    """,
                    (problem_type,),
                )
