$ErrorActionPreference = "Stop"

$Repo = "D:\notion-live-analyzer"
$Python = "$Repo\.venv\Scripts\python.exe"
$Root = "$Repo\sovereign_intelligence"

Write-Host "STAGE 19 BUILDER STARTING..."

if (!(Test-Path $Python)) {
    throw "Python executable not found."
}

if (!(Test-Path $Root)) {
    throw "sovereign_intelligence directory not found."
}

$backup = "$Repo\backups\stage19_$(Get-Date -Format yyyyMMdd_HHmmss)"
New-Item -ItemType Directory -Force $backup | Out-Null

if (Test-Path "$Root\execution") {
    Copy-Item "$Root\execution" "$backup\execution" -Recurse -Force
}

Write-Host "BACKUP_OK"

$adaptive = @"
from dataclasses import dataclass, field
from typing import Any

@dataclass
class RecoveryAttempt:
    attempt: int
    strategy: str
    reason: str
    status: str = "pending"
    result: Any = None

@dataclass
class AdaptiveResult:
    success: bool
    answer: str = ""
    attempts: list = field(default_factory=list)
    final_reason: str = ""
"@

Set-Content "$Root\execution\adaptive.py" $adaptive -Encoding utf8

$solver = @"
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
"@

Set-Content "$Root\execution\adaptive_solver.py" $solver -Encoding utf8

$exports = @"
from .planner import Planner
from .orchestrator import ExecutionEngine
from .adaptive import AdaptiveResult, RecoveryAttempt
from .adaptive_solver import AdaptiveSolver

__all__ = [
    "Planner",
    "ExecutionEngine",
    "AdaptiveResult",
    "RecoveryAttempt",
    "AdaptiveSolver",
]
"@

Set-Content "$Root\execution\__init__.py" $exports -Encoding utf8

Write-Host "FILES_CREATED"

& $Python -m compileall -q $Root

if ($LASTEXITCODE -ne 0) {
    throw "Compilation failed."
}

Write-Host "STAGE19_COMPILE_OK"

& $Python -c "from sovereign_intelligence.execution import AdaptiveSolver,AdaptiveResult,RecoveryAttempt; print('STAGE19_IMPORT_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Import test failed."
}

& $Python -c "from sovereign_intelligence.execution import AdaptiveSolver; r=AdaptiveSolver().solve(lambda p:'solution:'+p,'test'); assert r.success; assert r.answer=='solution:test'; print('STAGE19_SUCCESS_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Success test failed."
}

& $Python -c "from sovereign_intelligence.execution import AdaptiveSolver; s={'n':0}; f=lambda p: (_ for _ in ()).throw(RuntimeError('test failure')) if s.__setitem__('n',s['n']+1) or s['n']==1 else 'recovered'; r=AdaptiveSolver(3).solve(f,'test'); assert r.success; assert r.answer=='recovered'; print('STAGE19_RECOVERY_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Recovery test failed."
}

& $Python -c "from sovereign_intelligence import SovereignBrain; b=SovereignBrain(); assert hasattr(b,'solve'); print('STAGE19_BRAIN_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Brain compatibility failed."
}

Write-Host ""
Write-Host "============================================================"
Write-Host " STAGE 19 COMPLETE"
Write-Host "============================================================"
Write-Host "SOVEREIGN_STAGE19_INTEGRITY_OK"
