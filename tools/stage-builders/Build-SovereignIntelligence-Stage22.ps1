$ErrorActionPreference = "Stop"

$Repo = "D:\notion-live-analyzer"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$SI = Join-Path $Repo "sovereign_intelligence"

Write-Host ""
Write-Host "============================================================"
Write-Host " SOVEREIGN INTELLIGENCE - STAGE 22"
Write-Host " ADAPTIVE PROBLEM SOLVING"
Write-Host "============================================================"

if (!(Test-Path $Python)) {
    throw "Python not found: $Python"
}

if (!(Test-Path $SI)) {
    throw "Sovereign Intelligence directory not found."
}

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Repo "backups\stage22_$Stamp"

New-Item -ItemType Directory -Force -Path $Backup | Out-Null
Copy-Item -Path $SI -Destination $Backup -Recurse -Force

Write-Host "STAGE22_BACKUP_OK"

$Adaptive = Join-Path $SI "adaptive"

New-Item -ItemType Directory -Force -Path $Adaptive | Out-Null

@'
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdaptiveAttempt:
    number: int
    strategy: str
    success: bool
    confidence: float
    answer: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdaptiveResult:
    success: bool
    answer: str
    confidence: float
    attempts: list[AdaptiveAttempt] = field(default_factory=list)
    final_strategy: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
'@ | Set-Content -LiteralPath (Join-Path $Adaptive "models.py") -Encoding utf8

@'
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
'@ | Set-Content -LiteralPath (Join-Path $Adaptive "engine.py") -Encoding utf8

@'
from .models import AdaptiveAttempt, AdaptiveResult
from .engine import AdaptiveEngine

__all__ = [
    "AdaptiveAttempt",
    "AdaptiveResult",
    "AdaptiveEngine",
]
'@ | Set-Content -LiteralPath (Join-Path $Adaptive "__init__.py") -Encoding utf8

Write-Host "STAGE22_FILES_CREATED"

& $Python -m compileall -q $SI

if ($LASTEXITCODE -ne 0) {
    throw "Compilation failed"
}

Write-Host "STAGE22_COMPILE_OK"

& $Python -c "from sovereign_intelligence.adaptive import AdaptiveEngine, AdaptiveResult; print('STAGE22_IMPORT_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Import failed"
}

$Test = Join-Path $Repo "stage22_test.py"

@'
from sovereign_intelligence.adaptive import AdaptiveEngine

calls = []


def solver(problem, attempt, strategy):

    calls.append((attempt, strategy))

    if attempt == 1:
        return {
            "success": False,
            "confidence": 0.30,
            "answer": "retry",
        }

    return {
        "success": True,
        "confidence": 0.95,
        "answer": "validated solution",
    }


engine = AdaptiveEngine(
    max_attempts=3,
    minimum_confidence=0.70,
)

result = engine.run(
    "test problem",
    solver,
)

assert result.success
assert result.answer == "validated solution"
assert result.confidence >= 0.70
assert len(result.attempts) == 2
assert calls[0][1] == "direct"
assert calls[1][1] == "decompose"

print("STAGE22_ADAPTIVE_RECOVERY_OK")
print("ATTEMPTS=", len(result.attempts))
print("CONFIDENCE=", result.confidence)
'@ | Set-Content -LiteralPath $Test -Encoding utf8

& $Python $Test

if ($LASTEXITCODE -ne 0) {
    throw "Adaptive test failed"
}

Write-Host "STAGE22_RECOVERY_OK"

Remove-Item -LiteralPath $Test -Force -ErrorAction SilentlyContinue

& $Python -c "from sovereign_intelligence import SovereignBrain; b=SovereignBrain(); assert hasattr(b,'solve'); print('STAGE22_BRAIN_COMPATIBILITY_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Brain compatibility failed"
}

Write-Host ""
Write-Host "============================================================"
Write-Host " STAGE 22 COMPLETE"
Write-Host "============================================================"
Write-Host "SOVEREIGN_STAGE22_INTEGRITY_OK"
Write-Host ""
Write-Host "BACKUP:"
Write-Host $Backup
