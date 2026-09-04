$ErrorActionPreference = "Stop"

$Root = (Get-Location).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "============================================================"
Write-Host " SOVEREIGN INTELLIGENCE - STAGE 50"
Write-Host " GOVERNED DECISION PIPELINE"
Write-Host "============================================================"
Write-Host ""

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

$GovernanceDir = Join-Path $Root "sovereign_intelligence\execution\governance"
$TestDir = Join-Path $Root "tests\stage50"
$BackupDir = Join-Path $Root "backups\stage50"

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

if (-not (Test-Path $GovernanceDir)) {
    throw "Stage 49 governance package not found."
}

Write-Host "REPOSITORY_OK"
Write-Host "PYTHON_OK"
Write-Host "STAGE49_PACKAGE_FOUND"

# ------------------------------------------------------------
# Stage 48 baseline
# ------------------------------------------------------------

Write-Host ""
Write-Host "[2] Running Stage 48 baseline..."

& $Python -m pytest `
    --confcutdir=tests `
    ".\tests\stage48" `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "Stage 48 baseline failed. Stage 50 aborted."
}

Write-Host "STAGE48_BASELINE_OK"

# ------------------------------------------------------------
# Stage 49 baseline
# ------------------------------------------------------------

Write-Host ""
Write-Host "[3] Running Stage 49 baseline..."

& $Python -m pytest `
    --confcutdir=tests `
    ".\tests\stage49" `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "Stage 49 baseline failed. Stage 50 aborted."
}

Write-Host "STAGE49_BASELINE_OK"

# ------------------------------------------------------------
# Backup
# ------------------------------------------------------------

Write-Host ""
Write-Host "[4] Creating Stage 50 backup..."

New-Item `
    -ItemType Directory `
    -Force `
    -Path $BackupDir |
    Out-Null

$BackupTargets = @(
    "sovereign_intelligence\execution\governance",
    "tests\stage50"
)

foreach ($Target in $BackupTargets) {

    $Source = Join-Path $Root $Target

    if (Test-Path $Source) {

        $Leaf = Split-Path `
            $Target `
            -Leaf

        $Destination = Join-Path `
            $BackupDir `
            $Leaf

        Copy-Item `
            -Path $Source `
            -Destination $Destination `
            -Recurse `
            -Force
    }
}

Write-Host "BACKUP_OK"

# ------------------------------------------------------------
# Create Stage 50 test directory
# ------------------------------------------------------------

Write-Host ""
Write-Host "[5] Creating Stage 50 test directory..."

New-Item `
    -ItemType Directory `
    -Force `
    -Path $TestDir |
    Out-Null

Write-Host "TEST_DIRECTORY_OK"

# ------------------------------------------------------------
# Stage 50 pipeline
# ------------------------------------------------------------

Write-Host ""
Write-Host "[6] Creating governed decision pipeline..."

$Content = @'
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..control_models import ControlDecision
from ..decision_models import DecisionResult
from ..decision_control import DecisionControlEngine

from .governance import DecisionGovernanceEngine
from .models import DecisionRecord, GovernanceAssessment


@dataclass(frozen=True)
class GovernedDecision:
    """
    Complete Stage 50 governance result.

    This object preserves the relationship between the original
    decision, Stage 48 control output, Stage 49 governance record,
    and governance assessment.
    """

    decision_id: str
    decision: DecisionResult
    control: ControlDecision
    record: DecisionRecord
    assessment: GovernanceAssessment


class GovernedDecisionPipeline:
    """
    Stage 50 orchestration boundary for decision governance.

    This class composes existing Stage 48 and Stage 49 components.
    It does not replace or modify either component.
    """

    def __init__(
        self,
        control_engine: DecisionControlEngine | None = None,
        governance_engine: DecisionGovernanceEngine | None = None,
    ) -> None:
        self.control_engine = (
            control_engine
            or DecisionControlEngine()
        )

        self.governance_engine = (
            governance_engine
            or DecisionGovernanceEngine()
        )

    def run(
        self,
        decision: DecisionResult,
        evaluation: Any,
        *,
        decision_id: str,
        retry_count: int = 0,
        decision_confidence: float | None = None,
        evaluation_score: float | None = None,
        consensus: bool | None = None,
    ) -> GovernedDecision:
        """
        Execute the complete Stage 48 -> Stage 49 governance path.

        The original DecisionResult is treated as immutable input by
        this pipeline. The existing DecisionControlEngine remains the
        authority for determining the control action.
        """

        if not isinstance(
            decision,
            DecisionResult,
        ):
            raise TypeError(
                "decision must be a DecisionResult"
            )

        if not decision_id.strip():
            raise ValueError(
                "decision_id must not be empty"
            )

        if retry_count < 0:
            raise ValueError(
                "retry_count must be >= 0"
            )

        control = self.control_engine.decide(
            decision,
            evaluation,
            retry_count=retry_count,
        )

        resolved_decision_confidence = (
            decision.confidence
            if decision_confidence is None
            else decision_confidence
        )

        resolved_evaluation_score = (
            self._resolve_evaluation_score(
                evaluation
            )
            if evaluation_score is None
            else evaluation_score
        )

        resolved_consensus = (
            decision.consensus
            if consensus is None
            else consensus
        )

        record = self.governance_engine.record(
            control,
            decision_id=decision_id,
            decision_confidence=(
                resolved_decision_confidence
            ),
            evaluation_score=(
                resolved_evaluation_score
            ),
            consensus=resolved_consensus,
            retry_count=retry_count,
        )

        assessment = self.governance_engine.assess(
            record
        )

        return GovernedDecision(
            decision_id=decision_id,
            decision=decision,
            control=control,
            record=record,
            assessment=assessment,
        )

    @staticmethod
    def _resolve_evaluation_score(
        evaluation: Any,
    ) -> float:
        """
        Resolve a governance score from a supplied evaluation.

        Stage 50 does not invent a score for Stage 47's
        ResearchEvaluationEngine. If the evaluation object exposes
        an explicit overall_score, that value is used. Otherwise
        zero is passed to governance.
        """

        value = getattr(
            evaluation,
            "overall_score",
            0.0,
        )

        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
'@

$Content | Set-Content `
    -Encoding UTF8 `
    (Join-Path $GovernanceDir "pipeline.py")

Write-Host "PIPELINE_CREATED"

# ------------------------------------------------------------
# Update Stage 49 package exports
# ------------------------------------------------------------

Write-Host ""
Write-Host "[7] Updating governance package exports..."

$Content = @'
from .governance import DecisionGovernanceEngine
from .history import DecisionHistory
from .models import DecisionRecord, GovernanceAssessment
from .pipeline import GovernedDecision, GovernedDecisionPipeline

__all__ = [
    "DecisionGovernanceEngine",
    "DecisionHistory",
    "DecisionRecord",
    "GovernanceAssessment",
    "GovernedDecision",
    "GovernedDecisionPipeline",
]
'@

$Content | Set-Content `
    -Encoding UTF8 `
    (Join-Path $GovernanceDir "__init__.py")

Write-Host "EXPORTS_UPDATED"

# ------------------------------------------------------------
# Stage 50 tests
# ------------------------------------------------------------

Write-Host ""
Write-Host "[8] Creating Stage 50 tests..."

$Content = @'
from __future__ import annotations

from dataclasses import dataclass

import pytest

from sovereign_intelligence.execution.control_models import (
    ControlAction,
)
from sovereign_intelligence.execution.decision_models import (
    DecisionResult,
)
from sovereign_intelligence.execution.governance import (
    DecisionGovernanceEngine,
    DecisionHistory,
    GovernedDecision,
    GovernedDecisionPipeline,
)


@dataclass
class FakeEvaluation:
    overall_score: float = 0.90
    passed: bool = True
    weaknesses: list[str] | None = None
    recommendations: list[str] | None = None

    def __post_init__(self):
        if self.weaknesses is None:
            self.weaknesses = []

        if self.recommendations is None:
            self.recommendations = []


def make_decision(
    *,
    decision: str = "Use strategy A",
    confidence: float = 0.90,
    consensus: bool = True,
    conflicts: list[str] | None = None,
) -> DecisionResult:

    return DecisionResult(
        decision=decision,
        confidence=confidence,
        consensus=consensus,
        conflicts=conflicts or [],
        rationale="test rationale",
    )


def test_successful_pipeline_finalizes():

    pipeline = GovernedDecisionPipeline()

    decision = make_decision()

    result = pipeline.run(
        decision,
        FakeEvaluation(),
        decision_id="decision-1",
    )

    assert isinstance(
        result,
        GovernedDecision,
    )

    assert result.control.action is (
        ControlAction.FINALIZE
    )

    assert result.record.action is (
        ControlAction.FINALIZE
    )

    assert result.assessment.accepted is True


def test_failed_evaluation_retries():

    pipeline = GovernedDecisionPipeline()

    decision = make_decision(
        confidence=0.85,
    )

    evaluation = FakeEvaluation(
        overall_score=0.50,
        passed=False,
        weaknesses=["Incomplete answer"],
        recommendations=["Improve completeness"],
    )

    result = pipeline.run(
        decision,
        evaluation,
        decision_id="decision-1",
    )

    assert result.control.action is (
        ControlAction.RETRY
    )

    assert result.control.retryable is True


def test_objective_failure_replans():

    pipeline = GovernedDecisionPipeline()

    decision = make_decision(
        confidence=0.80,
    )

    evaluation = FakeEvaluation(
        overall_score=0.55,
        passed=False,
        weaknesses=[
            "Objective Alignment: weak"
        ],
        recommendations=[
            "Improve objective alignment."
        ],
    )

    result = pipeline.run(
        decision,
        evaluation,
        decision_id="decision-1",
    )

    assert result.control.action is (
        ControlAction.REPLAN
    )


def test_conflict_escalates():

    pipeline = GovernedDecisionPipeline()

    decision = make_decision(
        confidence=0.55,
        consensus=False,
        conflicts=[
            "Conflict between A and B"
        ],
    )

    result = pipeline.run(
        decision,
        FakeEvaluation(
            overall_score=0.70,
            passed=True,
        ),
        decision_id="decision-1",
    )

    assert result.control.action is (
        ControlAction.ESCALATE
    )

    assert result.assessment.escalation_detected is True


def test_retry_limit_rejects():

    pipeline = GovernedDecisionPipeline()

    decision = make_decision(
        confidence=0.50,
        consensus=False,
    )

    evaluation = FakeEvaluation(
        overall_score=0.40,
        passed=False,
    )

    result = pipeline.run(
        decision,
        evaluation,
        decision_id="decision-1",
        retry_count=2,
    )

    assert result.control.action is (
        ControlAction.REJECT
    )

    assert result.control.retryable is False


def test_history_is_preserved():

    history = DecisionHistory()

    governance = DecisionGovernanceEngine(
        history=history
    )

    pipeline = GovernedDecisionPipeline(
        governance_engine=governance
    )

    first = pipeline.run(
        make_decision(),
        FakeEvaluation(),
        decision_id="decision-1",
    )

    second = pipeline.run(
        make_decision(
            decision="Use strategy B",
            confidence=0.80,
        ),
        FakeEvaluation(
            overall_score=0.80,
        ),
        decision_id="decision-2",
    )

    assert first.record.decision_id == (
        "decision-1"
    )

    assert second.record.decision_id == (
        "decision-2"
    )

    assert history.count() == 2


def test_original_decision_is_preserved():

    decision = make_decision(
        confidence=0.91,
        consensus=True,
    )

    original = (
        decision.decision,
        decision.confidence,
        decision.consensus,
        list(decision.conflicts),
    )

    pipeline = GovernedDecisionPipeline()

    result = pipeline.run(
        decision,
        FakeEvaluation(),
        decision_id="decision-1",
    )

    assert result.decision is decision

    assert (
        decision.decision,
        decision.confidence,
        decision.consensus,
        list(decision.conflicts),
    ) == original


def test_invalid_decision_type_rejected():

    pipeline = GovernedDecisionPipeline()

    with pytest.raises(TypeError):
        pipeline.run(
            "not a decision",
            FakeEvaluation(),
            decision_id="decision-1",
        )


def test_empty_decision_id_rejected():

    pipeline = GovernedDecisionPipeline()

    with pytest.raises(ValueError):
        pipeline.run(
            make_decision(),
            FakeEvaluation(),
            decision_id="",
        )


def test_negative_retry_count_rejected():

    pipeline = GovernedDecisionPipeline()

    with pytest.raises(ValueError):
        pipeline.run(
            make_decision(),
            FakeEvaluation(),
            decision_id="decision-1",
            retry_count=-1,
        )


def test_explicit_governance_values_are_used():

    pipeline = GovernedDecisionPipeline()

    result = pipeline.run(
        make_decision(
            confidence=0.80,
            consensus=False,
        ),
        FakeEvaluation(
            overall_score=0.50,
            passed=False,
        ),
        decision_id="decision-1",
        decision_confidence=0.95,
        evaluation_score=0.95,
        consensus=True,
    )

    assert result.record.decision_confidence == 0.95
    assert result.record.evaluation_score == 0.95
    assert result.record.consensus is True


def test_stage47_style_evaluation_without_score_is_supported():

    pipeline = GovernedDecisionPipeline()

    class Stage47LikeEvaluation:
        pass

    result = pipeline.run(
        make_decision(
            confidence=0.80,
            consensus=False,
        ),
        Stage47LikeEvaluation(),
        decision_id="decision-1",
    )

    assert result.record.evaluation_score == 0.0


def test_repeated_execution_is_deterministic():

    pipeline = GovernedDecisionPipeline()

    decision = make_decision(
        confidence=0.90,
        consensus=True,
    )

    evaluation = FakeEvaluation(
        overall_score=0.90,
        passed=True,
    )

    first = pipeline.run(
        decision,
        evaluation,
        decision_id="decision-1",
    )

    second = pipeline.run(
        decision,
        evaluation,
        decision_id="decision-2",
    )

    assert first.control.action is (
        second.control.action
    )

    assert first.control.confidence == (
        second.control.confidence
    )


def test_governance_history_is_ordered():

    history = DecisionHistory()

    pipeline = GovernedDecisionPipeline(
        governance_engine=DecisionGovernanceEngine(
            history=history
        )
    )

    pipeline.run(
        make_decision(
            confidence=0.90
        ),
        FakeEvaluation(),
        decision_id="one",
    )

    pipeline.run(
        make_decision(
            confidence=0.80
        ),
        FakeEvaluation(
            overall_score=0.80
        ),
        decision_id="two",
    )

    assert history.actions() == (
        "finalize",
        "finalize",
    )
'@

$Content | Set-Content `
    -Encoding UTF8 `
    (Join-Path $TestDir "test_governed_pipeline.py")

Write-Host "TESTS_CREATED"

# ------------------------------------------------------------
# Validate generated files
# ------------------------------------------------------------

Write-Host ""
Write-Host "[9] Validating Stage 50 files..."

$RequiredFiles = @(
    (Join-Path $GovernanceDir "pipeline.py"),
    (Join-Path $GovernanceDir "__init__.py"),
    (Join-Path $TestDir "test_governed_pipeline.py")
)

foreach ($File in $RequiredFiles) {

    if (-not (Test-Path $File)) {
        throw "Required Stage 50 file missing: $File"
    }

    Write-Host "OK $File"
}

Write-Host "STAGE50_FILES_VALIDATED"

# ------------------------------------------------------------
# Compile Stage 50
# ------------------------------------------------------------

Write-Host ""
Write-Host "[10] Compiling Stage 50..."

& $Python -m py_compile `
    (Join-Path $GovernanceDir "pipeline.py") `
    (Join-Path $GovernanceDir "__init__.py") `
    (Join-Path $TestDir "test_governed_pipeline.py")

if ($LASTEXITCODE -ne 0) {
    throw "Stage 50 compilation failed."
}

Write-Host "STAGE50_COMPILE_OK"

# ------------------------------------------------------------
# Import validation
# ------------------------------------------------------------

Write-Host ""
Write-Host "[11] Validating Stage 50 imports..."

& $Python -c "from sovereign_intelligence.execution.governance import GovernedDecision, GovernedDecisionPipeline; print('STAGE50_IMPORT_VALIDATION_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 50 import validation failed."
}

# ------------------------------------------------------------
# Stage 50 tests
# ------------------------------------------------------------

Write-Host ""
Write-Host "[12] Running Stage 50 tests..."

& $Python -m pytest `
    --confcutdir=tests `
    ".\tests\stage50" `
    -v

if ($LASTEXITCODE -ne 0) {
    throw "Stage 50 tests failed."
}

Write-Host "STAGE50_TESTS_OK"

# ------------------------------------------------------------
# Full package compile
# ------------------------------------------------------------

Write-Host ""
Write-Host "[13] Compiling complete Sovereign Intelligence package..."

& $Python -m compileall -q ".\sovereign_intelligence"

if ($LASTEXITCODE -ne 0) {
    throw "Full package compilation failed."
}

Write-Host "FULL_SOVEREIGN_COMPILE_OK"

# ------------------------------------------------------------
# Stage 48 regression
# ------------------------------------------------------------

Write-Host ""
Write-Host "[14] Running Stage 48 regression..."

& $Python -m pytest `
    --confcutdir=tests `
    ".\tests\stage48" `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "Stage 48 regression failed."
}

Write-Host "STAGE48_REGRESSION_OK"

# ------------------------------------------------------------
# Stage 49 regression
# ------------------------------------------------------------

Write-Host ""
Write-Host "[15] Running Stage 49 regression..."

& $Python -m pytest `
    --confcutdir=tests `
    ".\tests\stage49" `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "Stage 49 regression failed."
}

Write-Host "STAGE49_REGRESSION_OK"

# ------------------------------------------------------------
# Core imports
# ------------------------------------------------------------

Write-Host ""
Write-Host "[16] Running core regression imports..."

& $Python -c "from sovereign_intelligence.orchestrator import SovereignBrain; from sovereign_intelligence.models import BrainResult; from sovereign_intelligence.execution.decision_control import DecisionControlEngine; from sovereign_intelligence.execution.governance import DecisionGovernanceEngine, GovernedDecisionPipeline; print('CORE_REGRESSION_IMPORT_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Core regression import failed."
}

# ------------------------------------------------------------
# Final status
# ------------------------------------------------------------

Write-Host ""
Write-Host "============================================================"
Write-Host " STAGE 50 BUILD COMPLETE"
Write-Host "============================================================"
Write-Host ""
Write-Host "STAGE50_COMPILE_OK"
Write-Host "STAGE50_IMPORT_VALIDATION_OK"
Write-Host "STAGE50_TESTS_OK"
Write-Host "FULL_SOVEREIGN_COMPILE_OK"
Write-Host "STAGE48_REGRESSION_OK"
Write-Host "STAGE49_REGRESSION_OK"
Write-Host "CORE_REGRESSION_IMPORT_OK"
Write-Host ""
Write-Host "Stage 50 Governed Decision Pipeline is installed."
Write-Host "Stage 48 remains unchanged."
Write-Host "Stage 49 governance semantics remain unchanged."
Write-Host "Orchestrator remains unchanged."
Write-Host ""