$ErrorActionPreference = "Stop"

$Repo = "D:\notion-live-analyzer"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$SI = Join-Path $Repo "sovereign_intelligence"

Write-Host ""
Write-Host "============================================================"
Write-Host " SOVEREIGN INTELLIGENCE - STAGE 24"
Write-Host " PERSISTENT LEARNING INTEGRATION"
Write-Host "============================================================"

if (!(Test-Path $Python)) {
    throw "Python executable not found."
}

if (!(Test-Path $SI)) {
    throw "Sovereign Intelligence directory not found."
}

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Repo "backups\stage24_$Stamp"

New-Item -ItemType Directory -Force -Path $Backup | Out-Null
Copy-Item -Path $SI -Destination $Backup -Recurse -Force

Write-Host "STAGE24_BACKUP_OK"

$Adaptive = Join-Path $SI "adaptive"

New-Item -ItemType Directory -Force -Path $Adaptive | Out-Null

@'
from .strategy_memory import StrategyMemory


class LearningCoordinator:

    def __init__(
        self,
        memory: StrategyMemory | None = None,
    ):
        self.memory = memory or StrategyMemory()

    def record_result(
        self,
        strategy: str,
        success: bool,
        confidence: float,
    ):
        self.memory.record(
            strategy=strategy,
            success=success,
            confidence=confidence,
        )

    def recommend(
        self,
        strategies: list[str],
    ) -> list[str]:

        if not strategies:
            return []

        return self.memory.recommend(
            strategies
        )

    def best_strategy(
        self,
        strategies: list[str],
    ) -> str | None:

        recommendations = self.recommend(
            strategies
        )

        if not recommendations:
            return None

        return recommendations[0]
'@ | Set-Content -LiteralPath (Join-Path $Adaptive "coordinator.py") -Encoding utf8

@'
from .coordinator import LearningCoordinator
from .strategy_memory import StrategyMemory, StrategyStats

__all__ = [
    "LearningCoordinator",
    "StrategyMemory",
    "StrategyStats",
]
'@ | Set-Content -LiteralPath (Join-Path $Adaptive "learning.py") -Encoding utf8

Write-Host "STAGE24_FILES_CREATED"

& $Python -m compileall -q $SI

if ($LASTEXITCODE -ne 0) {
    throw "Stage 24 compilation failed."
}

Write-Host "STAGE24_COMPILE_OK"

& $Python -c "from sovereign_intelligence.adaptive.learning import LearningCoordinator,StrategyMemory; print('STAGE24_IMPORT_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 24 import failed."
}

& $Python -c "from sovereign_intelligence.adaptive.learning import LearningCoordinator; from sovereign_intelligence.adaptive.strategy_memory import StrategyMemory; m=StrategyMemory('data/stage24_test.sqlite3'); c=LearningCoordinator(m); c.record_result('direct',False,0.20); c.record_result('decompose',True,0.90); assert c.best_strategy(['direct','decompose']) == 'decompose'; print('STAGE24_LEARNING_SELECTION_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Learning selection test failed."
}

Write-Host "STAGE24_LEARNING_SELECTION_TEST_OK"

& $Python -c "from sovereign_intelligence import SovereignBrain; b=SovereignBrain(); assert hasattr(b,'solve'); print('STAGE24_BRAIN_COMPATIBILITY_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Brain compatibility failed."
}

Write-Host ""
Write-Host "============================================================"
Write-Host " STAGE 24 COMPLETE"
Write-Host "============================================================"
Write-Host "SOVEREIGN_STAGE24_INTEGRITY_OK"
Write-Host ""
Write-Host "BACKUP:"
Write-Host $Backup
