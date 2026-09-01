$ErrorActionPreference = "Stop"

$Repo = "D:\notion-live-analyzer"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$SI = Join-Path $Repo "sovereign_intelligence"

Write-Host ""
Write-Host "============================================================"
Write-Host " SOVEREIGN INTELLIGENCE - STAGE 25"
Write-Host " GOAL & OBJECTIVE ENGINE"
Write-Host "============================================================"

if (!(Test-Path $Python)) {
    throw "Python executable not found."
}

if (!(Test-Path $SI)) {
    throw "Sovereign Intelligence directory not found."
}

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Repo "backups\stage25_$Stamp"

New-Item -ItemType Directory -Force -Path $Backup | Out-Null
Copy-Item -Path $SI -Destination $Backup -Recurse -Force

Write-Host "STAGE25_BACKUP_OK"

$Goals = Join-Path $SI "goals"

New-Item -ItemType Directory -Force -Path $Goals | Out-Null

@'
from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class Objective:
    id: str
    description: str
    priority: int = 50
    completed: bool = False
    progress: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Goal:
    id: str
    title: str
    description: str
    objectives: list[Objective] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        title: str,
        description: str,
        constraints: list[str] | None = None,
    ):
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            constraints=constraints or [],
        )
'@ | Set-Content -LiteralPath (Join-Path $Goals "models.py") -Encoding utf8

@'
from .models import Goal, Objective


class GoalEngine:

    def create_goal(
        self,
        title: str,
        description: str,
        constraints: list[str] | None = None,
    ) -> Goal:

        if not title.strip():
            raise ValueError("Goal title cannot be empty.")

        if not description.strip():
            raise ValueError(
                "Goal description cannot be empty."
            )

        return Goal.create(
            title=title,
            description=description,
            constraints=constraints,
        )

    def add_objective(
        self,
        goal: Goal,
        description: str,
        priority: int = 50,
    ) -> Objective:

        if not description.strip():
            raise ValueError(
                "Objective description cannot be empty."
            )

        priority = max(
            0,
            min(100, int(priority)),
        )

        objective = Objective(
            id=__import__("uuid").uuid4().__str__(),
            description=description,
            priority=priority,
        )

        goal.objectives.append(objective)

        return objective

    def update_progress(
        self,
        goal: Goal,
        objective_id: str,
        progress: float,
    ):

        progress = max(
            0.0,
            min(1.0, float(progress)),
        )

        for objective in goal.objectives:

            if objective.id == objective_id:

                objective.progress = progress
                objective.completed = progress >= 1.0

                self._refresh_status(goal)

                return objective

        raise KeyError(
            f"Objective not found: {objective_id}"
        )

    def _refresh_status(
        self,
        goal: Goal,
    ):

        if not goal.objectives:

            goal.status = "pending"
            return

        if all(
            objective.completed
            for objective in goal.objectives
        ):
            goal.status = "completed"
            return

        if any(
            objective.progress > 0
            for objective in goal.objectives
        ):
            goal.status = "in_progress"
            return

        goal.status = "pending"

    def completion(
        self,
        goal: Goal,
    ) -> float:

        if not goal.objectives:
            return 0.0

        total = sum(
            objective.progress
            for objective in goal.objectives
        )

        return total / len(goal.objectives)

    def prioritized_objectives(
        self,
        goal: Goal,
    ) -> list[Objective]:

        return sorted(
            goal.objectives,
            key=lambda item: item.priority,
            reverse=True,
        )
'@ | Set-Content -LiteralPath (Join-Path $Goals "engine.py") -Encoding utf8

@'
from .models import Goal, Objective
from .engine import GoalEngine

__all__ = [
    "Goal",
    "Objective",
    "GoalEngine",
]
'@ | Set-Content -LiteralPath (Join-Path $Goals "__init__.py") -Encoding utf8

Write-Host "STAGE25_FILES_CREATED"

& $Python -m compileall -q $SI

if ($LASTEXITCODE -ne 0) {
    throw "Stage 25 compilation failed."
}

Write-Host "STAGE25_COMPILE_OK"

& $Python -c "from sovereign_intelligence.goals import Goal, Objective, GoalEngine; print('STAGE25_IMPORT_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 25 import failed."
}

& $Python -c "from sovereign_intelligence.goals import GoalEngine; e=GoalEngine(); g=e.create_goal('Build AI','Build the intelligence platform'); o1=e.add_objective(g,'Create architecture',90); o2=e.add_objective(g,'Verify system',70); assert e.prioritized_objectives(g)[0].id == o1.id; e.update_progress(g,o1.id,1.0); assert g.status == 'in_progress'; e.update_progress(g,o2.id,1.0); assert g.status == 'completed'; assert e.completion(g) == 1.0; print('STAGE25_GOAL_ENGINE_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Goal engine test failed."
}

Write-Host "STAGE25_GOAL_TEST_OK"

& $Python -c "from sovereign_intelligence import SovereignBrain; b=SovereignBrain(); assert hasattr(b,'solve'); print('STAGE25_BRAIN_COMPATIBILITY_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Brain compatibility failed."
}

Write-Host ""
Write-Host "============================================================"
Write-Host " STAGE 25 COMPLETE"
Write-Host "============================================================"
Write-Host "SOVEREIGN_STAGE25_INTEGRITY_OK"
Write-Host ""
Write-Host "BACKUP:"
Write-Host $Backup
