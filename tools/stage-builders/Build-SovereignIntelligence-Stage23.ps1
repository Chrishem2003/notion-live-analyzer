$ErrorActionPreference = "Stop"

$Repo = "D:\notion-live-analyzer"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$SI = Join-Path $Repo "sovereign_intelligence"

Write-Host ""
Write-Host "============================================================"
Write-Host " SOVEREIGN INTELLIGENCE - STAGE 23"
Write-Host " ADAPTIVE LEARNING & STRATEGY MEMORY"
Write-Host "============================================================"

if (!(Test-Path $Python)) {
    throw "Python executable not found."
}

if (!(Test-Path $SI)) {
    throw "Sovereign Intelligence directory not found."
}

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Repo "backups\stage23_$Stamp"

New-Item -ItemType Directory -Force -Path $Backup | Out-Null
Copy-Item -Path $SI -Destination $Backup -Recurse -Force

Write-Host "STAGE23_BACKUP_OK"

$Adaptive = Join-Path $SI "adaptive"

New-Item -ItemType Directory -Force -Path $Adaptive | Out-Null

@'
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
'@ | Set-Content -LiteralPath (Join-Path $Adaptive "strategy_memory.py") -Encoding utf8

@'
from .strategy_memory import StrategyMemory, StrategyStats

__all__ = [
    "StrategyMemory",
    "StrategyStats",
]
'@ | Set-Content -LiteralPath (Join-Path $Adaptive "learning.py") -Encoding utf8

Write-Host "STAGE23_FILES_CREATED"

& $Python -m compileall -q $SI

if ($LASTEXITCODE -ne 0) {
    throw "Stage 23 compilation failed."
}

Write-Host "STAGE23_COMPILE_OK"

& $Python -c "from sovereign_intelligence.adaptive.strategy_memory import StrategyMemory,StrategyStats; print('STAGE23_IMPORT_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 23 import failed."
}

& $Python -c "from sovereign_intelligence.adaptive.strategy_memory import StrategyMemory; m=StrategyMemory('data/stage23_test.sqlite3'); m.record('direct',False,0.30); m.record('decompose',True,0.90); s=m.stats('decompose'); assert s.attempts == 1; assert s.successes == 1; assert s.success_rate == 1.0; print('STAGE23_LEARNING_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 23 learning test failed."
}

Write-Host "STAGE23_LEARNING_TEST_OK"

& $Python -c "from sovereign_intelligence import SovereignBrain; b=SovereignBrain(); assert hasattr(b,'solve'); print('STAGE23_BRAIN_COMPATIBILITY_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Brain compatibility failed."
}

Write-Host ""
Write-Host "============================================================"
Write-Host " STAGE 23 COMPLETE"
Write-Host "============================================================"
Write-Host "SOVEREIGN_STAGE23_INTEGRITY_OK"
Write-Host ""
Write-Host "BACKUP:"
Write-Host $Backup
