$ErrorActionPreference = "Stop"
# StrictMode enabled after variables are initialized.
Set-StrictMode -Version Latest

$Repo = "D:\notion-live-analyzer"
$Package = Join-Path $Repo "sovereign_intelligence"
$BackupRoot = Join-Path $Repo ("backups\sovereign_stage2_" + (Get-Date -Format "yyyyMMdd_HHmmss"))

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SOVEREIGN INTELLIGENCE — STAGE 2" -ForegroundColor Cyan
Write-Host " ADVANCED PROBLEM-SOLVING ORCHESTRATOR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $Repo)) {
    throw "Repository not found: $Repo"
}

if (-not (Test-Path $Package)) {
    throw "sovereign_intelligence package not found."
}

$Python = Join-Path $Repo ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment Python not found."
}

New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null

function Backup-Existing {
    param([string]$RelativePath)

    $Source = Join-Path $Repo $RelativePath

    if (Test-Path $Source) {

        $Destination = Join-Path $BackupRoot $RelativePath
        $Parent = Split-Path -Parent $Destination

        if ($Parent) {
            New-Item -ItemType Directory -Path $Parent -Force | Out-Null
        }

        Copy-Item $Source $Destination -Force

        Write-Host "[BACKUP] $RelativePath" -ForegroundColor Yellow
    }
}

function Write-Utf8 {
    param(
        [string]$RelativePath,
        [string]$Content
    )

    $Path = Join-Path $Repo $RelativePath
    $Parent = Split-Path -Parent $Path

    if ($Parent) {
        New-Item -ItemType Directory -Path $Parent -Force | Out-Null
    }

    [System.IO.File]::WriteAllText(
        $Path,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "[WRITE] $RelativePath" -ForegroundColor Green
}

Write-Host "[1/8] Backing up Stage 1 files..." -ForegroundColor Cyan

$FilesToBackup = @(
    "sovereign_intelligence\models.py",
    "sovereign_intelligence\orchestrator.py",
    "sovereign_intelligence\verification.py",
    "sovereign_intelligence\execution\planner.py",
    "sovereign_intelligence\execution\orchestrator.py",
    "sovereign_intelligence\config.py"
)

foreach ($File in $FilesToBackup) {
    Backup-Existing $File
}

Write-Host ""
Write-Host "[2/8] Building problem understanding engine..." -ForegroundColor Cyan

Write-Utf8 "sovereign_intelligence\intelligence\__init__.py" @'
from .classifier import ProblemClassifier
from .decomposer import ProblemDecomposer
from .critic import SolutionCritic
from .replanner import Replanner

__all__ = [
    "ProblemClassifier",
    "ProblemDecomposer",
    "SolutionCritic",
    "Replanner",
]
'@

Write-Utf8 "sovereign_intelligence\intelligence\classifier.py" @'
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass
class ProblemProfile:
    category: str
    complexity: str
    requires_research: bool
    requires_calculation: bool
    requires_code: bool
    requires_documents: bool
    requires_engineering: bool
    requires_tools: bool


class ProblemClassifier:

    def classify(self, prompt: str) -> ProblemProfile:

        text = prompt.lower()

        research = bool(
            re.search(
                r"\b(latest|current|research|source|citation|compare|find)\b",
                text,
            )
        )

        calculation = bool(
            re.search(
                r"\b(calculate|equation|math|percentage|statistics|formula|solve)\b",
                text,
            )
        )

        coding = bool(
            re.search(
                r"\b(code|python|javascript|bug|error|software|repository|github|api|program)\b",
                text,
            )
        )

        documents = bool(
            re.search(
                r"\b(pdf|document|contract|report|resume|cv|file)\b",
                text,
            )
        )

        engineering = bool(
            re.search(
                r"\b(cad|engineering|structure|mechanical|electrical|design|geometry)\b",
                text,
            )
        )

        tools = (
            research
            or coding
            or documents
            or engineering
        )

        categories = []

        if coding:
            categories.append("coding")

        if engineering:
            categories.append("engineering")

        if calculation:
            categories.append("mathematics")

        if research:
            categories.append("research")

        if documents:
            categories.append("documents")

        if not categories:
            categories.append("general")

        if len(categories) >= 3:
            complexity = "high"
        elif len(categories) == 2:
            complexity = "medium"
        else:
            complexity = "low"

        return ProblemProfile(
            category="multi-domain" if len(categories) > 1 else categories[0],
            complexity=complexity,
            requires_research=research,
            requires_calculation=calculation,
            requires_code=coding,
            requires_documents=documents,
            requires_engineering=engineering,
            requires_tools=tools,
        )
'@

Write-Utf8 "sovereign_intelligence\intelligence\decomposer.py" @'
from __future__ import annotations

import uuid

from ..models import Problem, Plan, PlanStep
from .classifier import ProblemProfile


class ProblemDecomposer:

    def decompose(
        self,
        problem: Problem,
        profile: ProblemProfile,
    ) -> Plan:

        steps = []

        steps.append(
            PlanStep(
                id=str(uuid.uuid4()),
                description="Understand the objective, constraints, assumptions and desired outcome.",
                agent="general",
            )
        )

        if profile.requires_research:
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Identify evidence requirements and research questions.",
                    agent="research",
                )
            )

        if profile.requires_code:
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Analyze the software architecture, failure mode or implementation requirement.",
                    agent="coding",
                )
            )

        if profile.requires_calculation:
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Perform quantitative reasoning and independently check important calculations.",
                    agent="mathematics",
                )
            )

        if profile.requires_engineering:
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Evaluate engineering assumptions, constraints and design implications.",
                    agent="engineering",
                )
            )

        if profile.requires_documents:
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Extract and analyze relevant document information.",
                    agent="document",
                )
            )

        steps.append(
            PlanStep(
                id=str(uuid.uuid4()),
                description="Synthesize the findings into a coherent candidate solution.",
                agent="general",
            )
        )

        steps.append(
            PlanStep(
                id=str(uuid.uuid4()),
                description="Critically evaluate the candidate solution for unsupported claims, contradictions and missing requirements.",
                agent="general",
            )
        )

        return Plan(
            objective=problem.objective,
            steps=steps,
            rationale=(
                f"Problem classified as {profile.category} "
                f"with {profile.complexity} complexity."
            ),
        )
'@

Write-Host ""
Write-Host "[3/8] Building critic and replanning system..." -ForegroundColor Cyan

Write-Utf8 "sovereign_intelligence\intelligence\critic.py" @'
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Critique:
    acceptable: bool
    issues: list[str]
    improvements: list[str]


class SolutionCritic:

    def evaluate(
        self,
        answer: str,
        original_problem: str,
    ) -> Critique:

        issues = []
        improvements = []

        if not answer.strip():
            issues.append("No solution was produced.")

        if len(answer.strip()) < 40:
            issues.append(
                "The solution is unusually short for a problem-solving task."
            )

        lower = answer.lower()

        if "i don't know" in lower:
            improvements.append(
                "Identify exactly what information is missing."
            )

        if "probably" in lower or "maybe" in lower:
            improvements.append(
                "Separate uncertainty from established conclusions."
            )

        if not issues:
            return Critique(
                acceptable=True,
                issues=[],
                improvements=improvements,
            )

        return Critique(
            acceptable=False,
            issues=issues,
            improvements=improvements,
        )
'@

Write-Utf8 "sovereign_intelligence\intelligence\replanner.py" @'
from __future__ import annotations

from ..models import Plan, PlanStep


class Replanner:

    def revise(
        self,
        plan: Plan,
        issues: list[str],
    ) -> Plan:

        revised_steps = list(plan.steps)

        revised_steps.append(
            PlanStep(
                id=f"revision-{len(revised_steps) + 1}",
                description=(
                    "Resolve critic findings: "
                    + "; ".join(issues)
                ),
                agent="general",
            )
        )

        return Plan(
            objective=plan.objective,
            steps=revised_steps,
            rationale=(
                plan.rationale
                + " Plan revised after critical evaluation."
            ),
        )
'@

Write-Host ""
Write-Host "[4/8] Upgrading execution engine..." -ForegroundColor Cyan

Write-Utf8 "sovereign_intelligence\execution\advanced.py" @'
from __future__ import annotations

from ..models import AIRequest, BrainResult, Problem, Plan
from ..providers.registry import ProviderRegistry
from ..agents.registry import AgentRegistry


class AdvancedExecutionEngine:

    def __init__(
        self,
        providers: ProviderRegistry,
        agents: AgentRegistry,
    ):
        self.providers = providers
        self.agents = agents

    def execute(
        self,
        problem: Problem,
        plan: Plan,
        provider_name: str,
        model: str,
        memory_context: str = "",
    ) -> BrainResult:

        provider = self.providers.get(provider_name)

        trace = []

        specialist_instructions = []

        for index, step in enumerate(plan.steps, start=1):

            agent = self.agents.get(step.agent)

            specialist_instructions.append(
                f"""
STEP {index}
Specialist: {agent.name}

Objective:
{step.description}

Specialist operating instructions:
{agent.instructions()}
"""
            )

        system = f"""
You are Sovereign Intelligence.

You are the central problem-solving engine of a
larger software platform.

You must solve problems rather than merely converse.

CORE PRINCIPLES

- Understand before answering.
- Decompose complex problems.
- Respect explicit constraints.
- Distinguish evidence from assumptions.
- Never fabricate actions.
- Never fabricate sources.
- Never claim a tool was used if it was not used.
- Identify uncertainty.
- Prefer testable solutions.
- Preserve existing software functionality.
- When several approaches exist, compare them.
- When a problem is underspecified, state the assumptions.
- For technical problems, prefer concrete implementation details.
- For numerical problems, verify calculations.
- For research problems, distinguish known information from claims
  requiring external verification.

EXECUTION PLAN

{chr(10).join(specialist_instructions)}

MEMORY CONTEXT

{memory_context[:12000]}

The final response should be useful to a technically sophisticated user.
"""

        prompt = f"""
ORIGINAL PROBLEM:

{problem.original}

Produce the best candidate solution.

Before the final answer, internally check:

1. Did you address the actual objective?
2. Did you respect constraints?
3. Did you introduce unsupported assumptions?
4. Did you miss an obvious part of the problem?
5. Are there technical or logical weaknesses?
6. Could the solution be made more actionable?

Return only the final user-facing solution.
"""

        response = provider.generate(
            AIRequest(
                prompt=prompt,
                system=system,
                model=model,
            )
        )

        trace.append(
            {
                "event": "advanced_execution",
                "provider": response.provider,
                "model": response.model,
                "steps": len(plan.steps),
                "usage": response.usage,
            }
        )

        return BrainResult(
            answer=response.text,
            plan=plan,
            provider=response.provider,
            model=response.model,
            execution_trace=trace,
        )
'@

Write-Host ""
Write-Host "[5/8] Building advanced brain controller..." -ForegroundColor Cyan

Backup-Existing "sovereign_intelligence\orchestrator.py"

Write-Utf8 "sovereign_intelligence\orchestrator.py" @'
from __future__ import annotations

from .config import BrainConfig
from .models import Problem, BrainResult
from .providers.registry import ProviderRegistry
from .agents.registry import AgentRegistry
from .memory import MemoryStore, MemoryManager
from .intelligence import (
    ProblemClassifier,
    ProblemDecomposer,
    SolutionCritic,
    Replanner,
)
from .execution.advanced import AdvancedExecutionEngine
from .verification import Verifier
from .safety.audit import AuditLogger


class SovereignBrain:

    def __init__(
        self,
        config: BrainConfig | None = None,
    ):

        self.config = (
            config
            or BrainConfig.from_env()
        )

        self.providers = ProviderRegistry.default()
        self.agents = AgentRegistry()

        self.memory_store = MemoryStore(
            self.config.memory_path
        )

        self.memory = MemoryManager(
            self.memory_store
        )

        self.classifier = ProblemClassifier()
        self.decomposer = ProblemDecomposer()
        self.critic = SolutionCritic()
        self.replanner = Replanner()

        self.executor = AdvancedExecutionEngine(
            self.providers,
            self.agents,
        )

        self.verifier = Verifier()

        self.audit = AuditLogger(
            self.config.audit_path
        )

    def solve(
        self,
        prompt: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> BrainResult:

        if not prompt.strip():
            raise ValueError(
                "Problem prompt cannot be empty."
            )

        selected_provider = (
            provider
            or self.config.default_provider
        )

        selected_model = (
            model
            or self.config.default_model
        )

        profile = self.classifier.classify(
            prompt
        )

        problem = Problem(
            original=prompt,
            objective=prompt,
            context={
                "category": profile.category,
                "complexity": profile.complexity,
            },
        )

        plan = self.decomposer.decompose(
            problem,
            profile,
        )

        memory_context = self.memory.context()

        trace = [
            {
                "event": "problem_classified",
                "category": profile.category,
                "complexity": profile.complexity,
            },
            {
                "event": "plan_created",
                "steps": len(plan.steps),
            },
        ]

        self.audit.record(
            "problem_started",
            {
                "category": profile.category,
                "complexity": profile.complexity,
                "provider": selected_provider,
                "model": selected_model,
            },
        )

        last_result = None

        for iteration in range(
            1,
            self.config.max_iterations + 1,
        ):

            trace.append(
                {
                    "event": "iteration_started",
                    "iteration": iteration,
                }
            )

            result = self.executor.execute(
                problem=problem,
                plan=plan,
                provider_name=selected_provider,
                model=selected_model,
                memory_context=memory_context,
            )

            last_result = result

            critique = self.critic.evaluate(
                result.answer,
                prompt,
            )

            trace.append(
                {
                    "event": "critique",
                    "iteration": iteration,
                    "acceptable": critique.acceptable,
                    "issues": critique.issues,
                }
            )

            if critique.acceptable:
                break

            if iteration >= self.config.max_iterations:
                break

            plan = self.replanner.revise(
                plan,
                critique.issues
                + critique.improvements,
            )

        if last_result is None:
            raise RuntimeError(
                "No execution result was produced."
            )

        verification = None

        if self.config.enable_verification:
            verification = self.verifier.evaluate(
                last_result.answer
            )

        last_result.plan = plan
        last_result.verification = verification
        last_result.execution_trace.extend(trace)

        self.memory.save_interaction(
            prompt,
            last_result.answer,
        )

        self.audit.record(
            "problem_completed",
            {
                "provider": last_result.provider,
                "model": last_result.model,
                "iterations": len(
                    [
                        x
                        for x in trace
                        if x["event"] == "iteration_started"
                    ]
                ),
                "verified": (
                    verification.passed
                    if verification
                    else None
                ),
            },
        )

        return last_result
'@

Write-Host ""
Write-Host "[6/8] Building intelligence diagnostics..." -ForegroundColor Cyan

Write-Utf8 "tools\Test-SovereignIntelligence-Stage2.ps1" @'
$ErrorActionPreference = "Stop"

$Repo = "D:\notion-live-analyzer"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"

Set-Location $Repo

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " SOVEREIGN INTELLIGENCE STAGE 2 TEST" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

& $Python -m compileall -q sovereign_intelligence

if ($LASTEXITCODE -ne 0) {
    throw "Compilation failed."
}

Write-Host "[OK] Compilation" -ForegroundColor Green

& $Python -c "from sovereign_intelligence import SovereignBrain; print('BRAIN_IMPORT_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Brain import failed."
}

& $Python -c "from sovereign_intelligence.intelligence import ProblemClassifier; p=ProblemClassifier().classify('Fix this Python error and research the current API'); print(p); assert p.requires_code; assert p.requires_research; print('CLASSIFIER_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Classifier test failed."
}

& $Python -c "from sovereign_intelligence.intelligence import ProblemDecomposer, ProblemClassifier; from sovereign_intelligence.models import Problem; p=Problem('Calculate the engineering design and research alternatives','Calculate the engineering design'); c=ProblemClassifier().classify(p.original); plan=ProblemDecomposer().decompose(p,c); print('PLAN_STEPS=',len(plan.steps)); assert len(plan.steps)>=3; print('DECOMPOSER_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Decomposer test failed."
}

Write-Host ""
Write-Host "STAGE 2 TESTS PASSED" -ForegroundColor Green
Write-Host ""
'@

Write-Host ""
Write-Host "[7/8] Creating Stage 2 documentation..." -ForegroundColor Cyan

Write-Utf8 "docs\sovereign_intelligence\STAGE2.md" @'
# Sovereign Intelligence — Stage 2

Stage 2 introduces the advanced problem-solving orchestration layer.

## Components

### Problem Classifier

Determines broad task characteristics:

- research
- coding
- mathematics
- documents
- engineering
- general
- multi-domain

### Problem Decomposer

Converts a problem into a sequence of specialist tasks.

### Advanced Execution Engine

Constructs a unified problem-solving context for the selected model.

### Solution Critic

Evaluates whether the candidate answer has obvious weaknesses.

### Replanner

Adds corrective work when the critic identifies a problem.

### Iterative solving

The brain can execute multiple planning iterations up to the configured limit.

## Safety

The Stage 2 system does not claim to have executed tools that have not actually
been connected.

Tool execution will be added in a later stage through the controlled tool
registry.
'@

Write-Host ""
Write-Host "[8/8] Running Stage 2 validation..." -ForegroundColor Cyan

& $Python -m compileall -q sovereign_intelligence

if ($LASTEXITCODE -ne 0) {
    throw "Final compilation failed."
}

& $Python -c "from sovereign_intelligence import SovereignBrain; print('SOVEREIGN_BRAIN_STAGE2_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Final brain import failed."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " STAGE 2 BUILD COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backup created at:" -ForegroundColor Yellow
Write-Host $BackupRoot
Write-Host ""
Write-Host "Run the detailed test:" -ForegroundColor Yellow
Write-Host ".\tools\Test-SovereignIntelligence-Stage2.ps1"
Write-Host ""