from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass
class StrategyStats:
    strategy: str
    attempts: int
    successes: int
    failures: int
    average_confidence: float

    @property
    def success_rate(self) -> float:
        if self.attempts == 0:
            return 0.0

        return self.successes / self.attempts


class StrategyMemory:

    def __init__(
        self,
        path: str = "data/strategy_memory.sqlite3",
    ):
        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _initialize(self):

        with self._connect() as db:

            db.execute(
                """
                CREATE TABLE IF NOT EXISTS strategy_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def record(
        self,
        strategy: str,
        success: bool,
        confidence: float,
    ):

        with self._connect() as db:

            db.execute(
                """
                INSERT INTO strategy_results
                (strategy, success, confidence)
                VALUES (?, ?, ?)
                """,
                (
                    strategy,
                    int(success),
                    float(confidence),
                ),
            )

    def stats(self, strategy: str) -> StrategyStats:

        with self._connect() as db:

            row = db.execute(
                """
                SELECT
                    COUNT(*),
                    COALESCE(SUM(success), 0),
                    COALESCE(AVG(confidence), 0)
                FROM strategy_results
                WHERE strategy = ?
                """,
                (strategy,),
            ).fetchone()

        attempts = int(row[0])
        successes = int(row[1])

        return StrategyStats(
            strategy=strategy,
            attempts=attempts,
            successes=successes,
            failures=attempts - successes,
            average_confidence=float(row[2]),
        )

    def recommend(self, strategies):

        ranked = []

        for strategy in strategies:

            stats = self.stats(strategy)

            ranked.append(
                (
                    stats.success_rate,
                    stats.average_confidence,
                    strategy,
                )
            )

        ranked.sort(
            key=lambda item: (
                item[0],
                item[1],
            ),
            reverse=True,
        )

        return [
            item[2]
            for item in ranked
        ]
