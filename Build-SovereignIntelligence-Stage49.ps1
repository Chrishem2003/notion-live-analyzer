$ErrorActionPreference = "Stop"

$Root = (Get-Location).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "============================================================"
Write-Host " SOVEREIGN INTELLIGENCE - STAGE 49"
Write-Host " DECISION GOVERNANCE AND HISTORY"
Write-Host "============================================================"
Write-Host ""

# ------------------------------------------------------------
# Stage 49 paths
# ------------------------------------------------------------

$GovernanceDir = Join-Path $Root "sovereign_intelligence\execution\governance"
$TestDir = Join-Path $Root "tests\stage49"
$BackupDir = Join-Path $Root "backups\stage49"

# ------------------------------------------------------------
# Preconditions
# ------------------------------------------------------------

Write-Host "[1] Checking repository..."

if (-not (Test-Path (Join-Path $Root ".git"))) {
    throw "Git repository not found."
}

if (-not (Test-Path $Python)) {
    throw "Virtual environment Python not found: $Python"
}

Write-Host "REPOSITORY_OK"
Write-Host "PYTHON_OK"

# ------------------------------------------------------------
# Stage 48 regression baseline
# ------------------------------------------------------------

Write-Host ""
Write-Host "[2] Running Stage 48 baseline..."

& $Python -m pytest `
    --confcutdir=tests `
    ".\tests\stage48" `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "Stage 48 baseline failed. Stage 49 build aborted."
}

Write-Host "STAGE48_BASELINE_OK"

# ------------------------------------------------------------
# Backup
# ------------------------------------------------------------

Write-Host ""
Write-Host "[3] Creating Stage 49 backup..."

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$BackupTargets = @(
    "sovereign_intelligence\execution\governance",
    "tests\stage49"
)

foreach ($Target in $BackupTargets) {
    $Source = Join-Path $Root $Target

    if (Test-Path $Source) {
        $Name = Split-Path $Target -Leaf
        $Destination = Join-Path $BackupDir $Name

        Copy-Item `
            -Path $Source `
            -Destination $Destination `
            -Recurse `
            -Force
    }
}

Write-Host "BACKUP_OK"

# ------------------------------------------------------------
# Create directories
# ------------------------------------------------------------

Write-Host ""
Write-Host "[4] Creating Stage 49 directories..."

New-Item -ItemType Directory -Force -Path $GovernanceDir | Out-Null
New-Item -ItemType Directory -Force -Path $TestDir | Out-Null

Write-Host "DIRECTORIES_OK"

# ------------------------------------------------------------
# Stage 49 package init
# ------------------------------------------------------------

$Content = @'
from .governance import DecisionGovernanceEngine
from .history import DecisionHistory
from .models import DecisionRecord, GovernanceAssessment

__all__ = [
    "DecisionGovernanceEngine",
    "DecisionHistory",
    "DecisionRecord",
    "GovernanceAssessment",
]
'@

$Content | Set-Content `
    -Encoding UTF8 `
    (Join-Path $GovernanceDir "__init__.py")

# ------------------------------------------------------------
# Stage 49 models
# ------------------------------------------------------------

$Content = @'
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..control_models import ControlAction


@dataclass(frozen=True)
class DecisionRecord:
    """
    Immutable governance record for one control decision.

    This layer records what Stage 48 decided without replacing
    DecisionControlEngine or changing its decision semantics.
    """

    decision_id: str
    action: ControlAction
    reason: str
    confidence: float
    retryable: bool
    decision_confidence: float
    evaluation_score: float
    consensus: bool
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernanceAssessment:
    """
    Assessment of a decision against its recorded history.
    """

    accepted: bool
    consistency_score: float
    confidence_stability: float
    repeated_action: bool
    escalation_detected: bool
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)
'@

$Content | Set-Content `
    -Encoding UTF8 `
    (Join-Path $GovernanceDir "models.py")

# ------------------------------------------------------------
# Stage 49 history
# ------------------------------------------------------------

$Content = @'
from __future__ import annotations

from collections.abc import Iterable

from .models import DecisionRecord


class DecisionHistory:
    """
    In-memory ordered history of governance decisions.

    The history layer is deliberately independent from the existing
    memory subsystem so Stage 49 can be introduced without changing
    existing memory contracts.
    """

    def __init__(
        self,
        records: Iterable[DecisionRecord] | None = None,
    ) -> None:
        self._records: list[DecisionRecord] = list(records or [])

    def append(self, record: DecisionRecord) -> None:
        if not isinstance(record, DecisionRecord):
            raise TypeError("record must be a DecisionRecord")

        self._records.append(record)

    def all(self) -> tuple[DecisionRecord, ...]:
        return tuple(self._records)

    def latest(self) -> DecisionRecord | None:
        if not self._records:
            return None

        return self._records[-1]

    def count(self) -> int:
        return len(self._records)

    def actions(self) -> tuple[str, ...]:
        return tuple(record.action.value for record in self._records)

    def recent(
        self,
        limit: int = 5,
    ) -> tuple[DecisionRecord, ...]:
        if limit < 0:
            raise ValueError("limit must be >= 0")

        if limit == 0:
            return ()

        return tuple(self._records[-limit:])
'@

$Content | Set-Content `
    -Encoding UTF8 `
    (Join-Path $GovernanceDir "history.py")

# ------------------------------------------------------------
# Stage 49 governance engine
# ------------------------------------------------------------

$Content = @'
from __future__ import annotations

from typing import Any

from ..control_models import ControlAction, ControlDecision
from .history import DecisionHistory
from .models import DecisionRecord, GovernanceAssessment


class DecisionGovernanceEngine:
    """
    Stage 49 governance layer.

    It observes Stage 48 ControlDecision objects and evaluates
    consistency across decision history.

    It does NOT replace DecisionControlEngine.
    """

    def __init__(
        self,
        history: DecisionHistory | None = None,
        minimum_consistency: float = 0.60,
    ) -> None:
        if not 0.0 <= minimum_consistency <= 1.0:
            raise ValueError(
                "minimum_consistency must be between 0 and 1"
            )

        self.history = history or DecisionHistory()
        self.minimum_consistency = minimum_consistency

    def record(
        self,
        control_decision: ControlDecision,
        *,
        decision_id: str,
        decision_confidence: float = 0.0,
        evaluation_score: float = 0.0,
        consensus: bool = False,
        retry_count: int = 0,
    ) -> DecisionRecord:
        if not isinstance(control_decision, ControlDecision):
            raise TypeError(
                "control_decision must be a ControlDecision"
            )

        if not decision_id.strip():
            raise ValueError("decision_id must not be empty")

        if retry_count < 0:
            raise ValueError("retry_count must be >= 0")

        record = DecisionRecord(
            decision_id=decision_id,
            action=control_decision.action,
            reason=control_decision.reason,
            confidence=self._bounded(control_decision.confidence),
            retryable=control_decision.retryable,
            decision_confidence=self._bounded(decision_confidence),
            evaluation_score=self._bounded(evaluation_score),
            consensus=bool(consensus),
            retry_count=retry_count,
            metadata=dict(control_decision.metadata),
        )

        self.history.append(record)

        return record

    def assess(
        self,
        record: DecisionRecord | None = None,
    ) -> GovernanceAssessment:
        target = record or self.history.latest()

        if target is None:
            return GovernanceAssessment(
                accepted=False,
                consistency_score=0.0,
                confidence_stability=0.0,
                repeated_action=False,
                escalation_detected=False,
                reason="No decision record is available.",
            )

        previous = [
            item
            for item in self.history.all()
            if item.decision_id != target.decision_id
        ]

        if not previous:
            return GovernanceAssessment(
                accepted=True,
                consistency_score=1.0,
                confidence_stability=1.0,
                repeated_action=False,
                escalation_detected=(
                    target.action is ControlAction.ESCALATE
                ),
                reason=(
                    "First recorded decision has no prior history "
                    "against which to compare."
                ),
            )

        same_action = sum(
            item.action is target.action
            for item in previous
        )

        consistency_score = same_action / len(previous)

        previous_confidences = [
            item.confidence
            for item in previous
        ]

        average_previous = (
            sum(previous_confidences)
            / len(previous_confidences)
        )

        confidence_stability = max(
            0.0,
            1.0 - abs(
                target.confidence - average_previous
            ),
        )

        repeated_action = same_action > 0

        escalation_detected = (
            target.action is ControlAction.ESCALATE
            or any(
                item.action is ControlAction.ESCALATE
                for item in previous
            )
        )

        accepted = (
            consistency_score >= self.minimum_consistency
            or target.action in {
                ControlAction.FINALIZE,
                ControlAction.REPLAN,
            }
        )

        if accepted:
            reason = (
                "Decision is consistent with governance history "
                "under the configured policy."
            )
        else:
            reason = (
                "Decision differs materially from prior control "
                "actions and requires governance attention."
            )

        return GovernanceAssessment(
            accepted=accepted,
            consistency_score=round(
                consistency_score,
                4,
            ),
            confidence_stability=round(
                confidence_stability,
                4,
            ),
            repeated_action=repeated_action,
            escalation_detected=escalation_detected,
            reason=reason,
            metadata={
                "history_size": len(previous),
                "same_action_count": same_action,
                "target_action": target.action.value,
            },
        )

    @staticmethod
    def _bounded(value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0

        return max(
            0.0,
            min(1.0, numeric),
        )
'@

$Content | Set-Content `
    -Encoding UTF8 `
    (Join-Path $GovernanceDir "governance.py")

# ------------------------------------------------------------
# Stage 49 tests
# ------------------------------------------------------------

$Content = @'
from __future__ import annotations

from sovereign_intelligence.execution.control_models import (
    ControlAction,
    ControlDecision,
)
from sovereign_intelligence.execution.governance import (
    DecisionGovernanceEngine,
    DecisionHistory,
)


def make_control(
    action: ControlAction = ControlAction.FINALIZE,
    confidence: float = 0.90,
) -> ControlDecision:
    return ControlDecision(
        action=action,
        reason="test decision",
        confidence=confidence,
        retryable=action in {
            ControlAction.RETRY,
            ControlAction.REPLAN,
        },
        metadata={"source": "stage49-test"},
    )


def test_first_record_is_accepted():
    engine = DecisionGovernanceEngine()

    record = engine.record(
        make_control(),
        decision_id="decision-1",
        decision_confidence=0.90,
        evaluation_score=0.90,
        consensus=True,
    )

    assessment = engine.assess(record)

    assert record.action is ControlAction.FINALIZE
    assert assessment.accepted is True
    assert assessment.consistency_score == 1.0


def test_history_preserves_order():
    history = DecisionHistory()
    engine = DecisionGovernanceEngine(history)

    engine.record(
        make_control(ControlAction.RETRY, 0.50),
        decision_id="decision-1",
    )

    engine.record(
        make_control(ControlAction.REPLAN, 0.60),
        decision_id="decision-2",
    )

    assert history.count() == 2
    assert history.actions() == (
        "retry",
        "replan",
    )


def test_repeated_action_is_detected():
    engine = DecisionGovernanceEngine()

    first = engine.record(
        make_control(ControlAction.RETRY, 0.60),
        decision_id="decision-1",
    )

    engine.record(
        make_control(ControlAction.RETRY, 0.62),
        decision_id="decision-2",
    )

    assessment = engine.assess(first)

    assert assessment.repeated_action is True


def test_escalation_is_detected():
    engine = DecisionGovernanceEngine()

    engine.record(
        make_control(ControlAction.ESCALATE, 0.40),
        decision_id="decision-1",
    )

    latest = engine.record(
        make_control(ControlAction.RETRY, 0.50),
        decision_id="decision-2",
    )

    assessment = engine.assess(latest)

    assert assessment.escalation_detected is True


def test_confidence_stability_is_bounded():
    engine = DecisionGovernanceEngine()

    engine.record(
        make_control(ControlAction.FINALIZE, 0.90),
        decision_id="decision-1",
    )

    latest = engine.record(
        make_control(ControlAction.FINALIZE, 0.80),
        decision_id="decision-2",
    )

    assessment = engine.assess(latest)

    assert 0.0 <= assessment.confidence_stability <= 1.0


def test_empty_history_is_not_accepted():
    engine = DecisionGovernanceEngine()

    assessment = engine.assess()

    assert assessment.accepted is False
    assert assessment.consistency_score == 0.0


def test_invalid_decision_id_rejected():
    engine = DecisionGovernanceEngine()

    try:
        engine.record(
            make_control(),
            decision_id="",
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError for empty decision_id"
        )


def test_control_decision_is_not_modified():
    control = make_control(
        ControlAction.FINALIZE,
        0.91,
    )

    engine = DecisionGovernanceEngine()

    engine.record(
        control,
        decision_id="decision-1",
    )

    assert control.action is ControlAction.FINALIZE
    assert control.confidence == 0.91
    assert control.retryable is False
'@

$Content | Set-Content `
    -Encoding UTF8 `
    (Join-Path $TestDir "test_governance.py")

# ------------------------------------------------------------
# Validation: files
# ------------------------------------------------------------

Write-Host ""
Write-Host "[5] Validating generated files..."

$RequiredFiles = @(
    (Join-Path $GovernanceDir "__init__.py"),
    (Join-Path $GovernanceDir "models.py"),
    (Join-Path $GovernanceDir "history.py"),
    (Join-Path $GovernanceDir "governance.py"),
    (Join-Path $TestDir "test_governance.py")
)

foreach ($File in $RequiredFiles) {
    if (-not (Test-Path $File)) {
        throw "Required Stage 49 file missing: $File"
    }

    Write-Host "OK $File"
}

Write-Host "FILES_VALIDATED"

# ------------------------------------------------------------
# Stage 49 compile
# ------------------------------------------------------------

Write-Host ""
Write-Host "[6] Compiling Stage 49..."

& $Python -m py_compile `
    (Join-Path $GovernanceDir "__init__.py") `
    (Join-Path $GovernanceDir "models.py") `
    (Join-Path $GovernanceDir "history.py") `
    (Join-Path $GovernanceDir "governance.py") `
    (Join-Path $TestDir "test_governance.py")

if ($LASTEXITCODE -ne 0) {
    throw "Stage 49 compilation failed."
}

Write-Host "STAGE49_COMPILE_OK"

# ------------------------------------------------------------
# Stage 49 import validation
# ------------------------------------------------------------

Write-Host ""
Write-Host "[7] Validating Stage 49 imports..."

& $Python -c "from sovereign_intelligence.execution.governance import DecisionGovernanceEngine, DecisionHistory, DecisionRecord, GovernanceAssessment; print('STAGE49_IMPORT_VALIDATION_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 49 import validation failed."
}

# ------------------------------------------------------------
# Stage 49 tests
# ------------------------------------------------------------

Write-Host ""
Write-Host "[8] Running Stage 49 tests..."

& $Python -m pytest `
    --confcutdir=tests `
    ".\tests\stage49" `
    -v

if ($LASTEXITCODE -ne 0) {
    throw "Stage 49 tests failed."
}

Write-Host "STAGE49_TESTS_OK"

# ------------------------------------------------------------
# Full package compile
# ------------------------------------------------------------

Write-Host ""
Write-Host "[9] Compiling complete Sovereign Intelligence package..."

& $Python -m compileall -q ".\sovereign_intelligence"

if ($LASTEXITCODE -ne 0) {
    throw "Full Sovereign Intelligence compilation failed."
}

Write-Host "FULL_SOVEREIGN_COMPILE_OK"

# ------------------------------------------------------------
# Stage 48 regression
# ------------------------------------------------------------

Write-Host ""
Write-Host "[10] Running Stage 48 regression..."

& $Python -m pytest `
    --confcutdir=tests `
    ".\tests\stage48" `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "Stage 48 regression failed."
}

Write-Host "STAGE48_REGRESSION_OK"

# ------------------------------------------------------------
# Core regression imports
# ------------------------------------------------------------

Write-Host ""
Write-Host "[11] Running core regression imports..."

& $Python -c "from sovereign_intelligence.orchestrator import SovereignBrain; from sovereign_intelligence.models import BrainResult; from sovereign_intelligence.execution.decision_control import DecisionControlEngine; from sovereign_intelligence.execution.governance import DecisionGovernanceEngine; print('CORE_REGRESSION_IMPORT_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Core regression import failed."
}

# ------------------------------------------------------------
# Final status
# ------------------------------------------------------------

Write-Host ""
Write-Host "============================================================"
Write-Host " STAGE 49 BUILD COMPLETE"
Write-Host "============================================================"
Write-Host ""
Write-Host "STAGE49_COMPILE_OK"
Write-Host "STAGE49_IMPORT_VALIDATION_OK"
Write-Host "STAGE49_TESTS_OK"
Write-Host "FULL_SOVEREIGN_COMPILE_OK"
Write-Host "STAGE48_REGRESSION_OK"
Write-Host "CORE_REGRESSION_IMPORT_OK"
Write-Host ""
Write-Host "Stage 49 Decision Governance is installed."
Write-Host "Stage 48 remains unchanged."
Write-Host "Orchestrator remains unchanged."
Write-Host ""
