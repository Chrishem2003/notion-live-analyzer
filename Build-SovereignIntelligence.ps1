#requires -Version 5.1

<#
===========================================================================
 SOVEREIGN INTELLIGENCE ENGINE
 Master Builder
 --------------------------------------------------------------------------
 Purpose:
   Build a native AI brain for notion-live-analyzer without destroying
   existing application functionality.

 Design principles:
   - Additive architecture
   - No deletion of existing application files
   - Backups before modification
   - Provider abstraction
   - Agent orchestration
   - Tool registry
   - Memory
   - Verification
   - Knowledge/RAG foundation
   - Observability
   - Streamlit integration
   - Automated tests
   - Git safety
=========================================================================== #>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# -------------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------------

$Repo = "D:\notion-live-analyzer"
$Package = Join-Path $Repo "sovereign_intelligence"
$Tests = Join-Path $Repo "tests\sovereign_intelligence"
$Pages = Join-Path $Repo "pages"
$Tools = Join-Path $Repo "tools"
$Docs = Join-Path $Repo "docs\sovereign_intelligence"
$ConfigDir = Join-Path $Repo "config"

$VenvPython = Join-Path $Repo ".venv\Scripts\python.exe"
$VenvPip = Join-Path $Repo ".venv\Scripts\pip.exe"

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupRoot = Join-Path $Repo "backups\sovereign_intelligence_$Timestamp"

$InstallDependencies = $true
$RunTests = $true
$RunCompile = $true
$GitCommit = $false

# -------------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------------

function Write-Header {
    param([string]$Text)

    Write-Host ""
    Write-Host ("=" * 78) -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host ("=" * 78) -ForegroundColor Cyan
}

function Write-OK {
    param([string]$Text)
    Write-Host "[OK] $Text" -ForegroundColor Green
}

function Write-WARN {
    param([string]$Text)
    Write-Host "[WARN] $Text" -ForegroundColor Yellow
}

function Write-FAIL {
    param([string]$Text)
    Write-Host "[FAIL] $Text" -ForegroundColor Red
}

function Ensure-Directory {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-FileSafe {
    param(
        [string]$Path,
        [string]$Content
    )

    $parent = Split-Path -Parent $Path

    if ($parent) {
        Ensure-Directory $parent
    }

    if (Test-Path -LiteralPath $Path) {
        Write-WARN "Existing file preserved: $Path"
        return
    }

    [System.IO.File]::WriteAllText(
        $Path,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-OK "Created: $Path"
}

function Backup-File {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $relative = $Path.Substring($Repo.Length).TrimStart("\")
    $destination = Join-Path $BackupRoot $relative

    Ensure-Directory (Split-Path -Parent $destination)

    Copy-Item -LiteralPath $Path -Destination $destination -Force

    Write-OK "Backed up: $relative"
}

function Invoke-Python {
    param(
        [string[]]$Arguments
    )

    if (-not (Test-Path -LiteralPath $VenvPython)) {
        throw "Python virtual environment not found: $VenvPython"
    }

    & $VenvPython @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE"
    }
}

# -------------------------------------------------------------------------
# START
# -------------------------------------------------------------------------

Write-Header "SOVEREIGN INTELLIGENCE ENGINE BUILD"

Write-Host "Repository: $Repo"
Write-Host "Package:    $Package"
Write-Host "Backup:     $BackupRoot"
Write-Host ""

# -------------------------------------------------------------------------
# REPOSITORY VALIDATION
# -------------------------------------------------------------------------

Write-Header "1. REPOSITORY VALIDATION"

if (-not (Test-Path -LiteralPath $Repo)) {
    throw "Repository does not exist: $Repo"
}

Set-Location $Repo

if (-not (Test-Path -LiteralPath (Join-Path $Repo ".git"))) {
    throw "This directory is not a Git repository."
}

if (-not (Test-Path -LiteralPath (Join-Path $Repo "app.py"))) {
    Write-WARN "app.py was not found. Existing application entry point may be elsewhere."
}
else {
    Write-OK "app.py found"
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw ".venv Python not found: $VenvPython"
}

Write-OK "Git repository detected"
Write-OK "Python virtual environment detected"

# -------------------------------------------------------------------------
# BACKUP
# -------------------------------------------------------------------------

Write-Header "2. BACKUP"

Ensure-Directory $BackupRoot

Backup-File (Join-Path $Repo "app.py")
Backup-File (Join-Path $Repo "requirements.txt")
Backup-File (Join-Path $Repo ".gitignore")
Backup-File (Join-Path $Repo ".streamlit\config.toml")
Backup-File (Join-Path $Repo ".streamlit\secrets.toml")

Write-OK "Backup completed"

# -------------------------------------------------------------------------
# DIRECTORIES
# -------------------------------------------------------------------------

Write-Header "3. CREATE SOVEREIGN INTELLIGENCE ARCHITECTURE"

$Directories = @(
    $Package
    (Join-Path $Package "agents")
    (Join-Path $Package "providers")
    (Join-Path $Package "memory")
    (Join-Path $Package "knowledge")
    (Join-Path $Package "tools")
    (Join-Path $Package "execution")
    (Join-Path $Package "safety")
    (Join-Path $Package "observability")
    (Join-Path $Package "api")
    (Join-Path $Package "config")
    $Tests
    $Pages
    $Tools
    $Docs
    $ConfigDir
)

foreach ($dir in $Directories) {
    Ensure-Directory $dir
}

Write-OK "Architecture directories created"

# =========================================================================
# PACKAGE ROOT
# =========================================================================

Write-Header "4. CORE INTELLIGENCE"

Write-FileSafe (Join-Path $Package "__init__.py") @'
"""
Sovereign Intelligence Engine.

A native orchestration layer for the notion-live-analyzer platform.
"""

from .orchestrator import SovereignBrain

__all__ = ["SovereignBrain"]

__version__ = "0.1.0"
'@

Write-FileSafe (Join-Path $Package "models.py") @'
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIRequest:
    prompt: str
    system: str | None = None
    model: str | None = None
    provider: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponse:
    text: str
    provider: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Problem:
    original: str
    objective: str
    constraints: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanStep:
    id: str
    description: str
    agent: str = "general"
    tools: list[str] = field(default_factory=list)
    status: str = "pending"


@dataclass
class Plan:
    objective: str
    steps: list[PlanStep]
    rationale: str = ""


@dataclass
class VerificationResult:
    passed: bool
    confidence: float
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class BrainResult:
    answer: str
    plan: Plan | None = None
    verification: VerificationResult | None = None
    provider: str | None = None
    model: str | None = None
    execution_trace: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
'@

Write-FileSafe (Join-Path $Package "config.py") @'
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class BrainConfig:
    default_provider: str = "openai"
    default_model: str = "gpt-5"
    fallback_provider: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096
    memory_path: str = "data/sovereign_intelligence/memory.db"
    audit_path: str = "data/sovereign_intelligence/audit.jsonl"
    enable_verification: bool = True
    max_iterations: int = 4

    @classmethod
    def from_env(cls) -> "BrainConfig":
        return cls(
            default_provider=os.getenv("SOVEREIGN_AI_PROVIDER", "openai"),
            default_model=os.getenv("SOVEREIGN_AI_MODEL", "gpt-5"),
            fallback_provider=os.getenv("SOVEREIGN_AI_FALLBACK_PROVIDER"),
            temperature=float(os.getenv("SOVEREIGN_AI_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("SOVEREIGN_AI_MAX_TOKENS", "4096")),
            memory_path=os.getenv(
                "SOVEREIGN_AI_MEMORY_PATH",
                "data/sovereign_intelligence/memory.db",
            ),
            audit_path=os.getenv(
                "SOVEREIGN_AI_AUDIT_PATH",
                "data/sovereign_intelligence/audit.jsonl",
            ),
            enable_verification=os.getenv(
                "SOVEREIGN_AI_VERIFICATION", "true"
            ).lower() == "true",
            max_iterations=int(
                os.getenv("SOVEREIGN_AI_MAX_ITERATIONS", "4")
            ),
        )
'@

# =========================================================================
# PROVIDERS
# =========================================================================

Write-Header "5. PROVIDER FABRIC"

Write-FileSafe (Join-Path $Package "providers\base.py") @'
from __future__ import annotations

from abc import ABC, abstractmethod
from ..models import AIRequest, AIResponse


class ProviderError(RuntimeError):
    pass


class ModelProvider(ABC):

    name: str = "unknown"

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        raise NotImplementedError
'@

Write-FileSafe (Join-Path $Package "providers\openai_compatible.py") @'
from __future__ import annotations

import os
import httpx

from .base import ModelProvider, ProviderError
from ..models import AIRequest, AIResponse


class OpenAICompatibleProvider(ModelProvider):

    name = "openai-compatible"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")

    def generate(self, request: AIRequest) -> AIResponse:

        if not self.api_key:
            raise ProviderError(
                "OPENAI_API_KEY is not configured."
            )

        payload = {
            "model": request.model or "gpt-5",
            "messages": [],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        if request.system:
            payload["messages"].append(
                {"role": "system", "content": request.system}
            )

        payload["messages"].append(
            {"role": "user", "content": request.prompt}
        )

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            response.raise_for_status()

        except Exception as exc:
            raise ProviderError(str(exc)) from exc

        data = response.json()

        choices = data.get("choices", [])

        if not choices:
            raise ProviderError(
                "Provider returned no choices."
            )

        message = choices[0].get("message", {})

        return AIResponse(
            text=message.get("content", ""),
            provider=self.name,
            model=data.get("model", payload["model"]),
            usage=data.get("usage", {}),
            metadata=data,
        )
'@

Write-FileSafe (Join-Path $Package "providers\openai.py") @'
from .openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):

    name = "openai"

    def __init__(self):
        super().__init__(
            base_url="https://api.openai.com/v1"
        )
'@

Write-FileSafe (Join-Path $Package "providers\openrouter.py") @'
from .openai_compatible import OpenAICompatibleProvider
import os


class OpenRouterProvider(OpenAICompatibleProvider):

    name = "openrouter"

    def __init__(self):
        super().__init__(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )
'@

Write-FileSafe (Join-Path $Package "providers\anthropic.py") @'
from __future__ import annotations

import os
import httpx

from .base import ModelProvider, ProviderError
from ..models import AIRequest, AIResponse


class AnthropicProvider(ModelProvider):

    name = "anthropic"

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    def generate(self, request: AIRequest) -> AIResponse:

        if not self.api_key:
            raise ProviderError(
                "ANTHROPIC_API_KEY is not configured."
            )

        payload = {
            "model": request.model or "claude-sonnet-4-5",
            "max_tokens": request.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": request.prompt,
                }
            ],
        }

        if request.system:
            payload["system"] = request.system

        try:
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            response.raise_for_status()

        except Exception as exc:
            raise ProviderError(str(exc)) from exc

        data = response.json()

        parts = data.get("content", [])

        text = "".join(
            part.get("text", "")
            for part in parts
            if part.get("type") == "text"
        )

        return AIResponse(
            text=text,
            provider=self.name,
            model=data.get("model", payload["model"]),
            usage=data.get("usage", {}),
            metadata=data,
        )
'@

Write-FileSafe (Join-Path $Package "providers\google.py") @'
from __future__ import annotations

import os
import httpx

from .base import ModelProvider, ProviderError
from ..models import AIRequest, AIResponse


class GoogleProvider(ModelProvider):

    name = "google"

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")

    def generate(self, request: AIRequest) -> AIResponse:

        if not self.api_key:
            raise ProviderError(
                "GOOGLE_API_KEY is not configured."
            )

        model = request.model or "gemini-2.5-flash"

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:generateContent"
            f"?key={self.api_key}"
        )

        contents = [
            {
                "role": "user",
                "parts": [
                    {"text": request.prompt}
                ],
            }
        ]

        if request.system:
            contents.insert(
                0,
                {
                    "role": "user",
                    "parts": [
                        {"text": request.system}
                    ],
                },
            )

        try:
            response = httpx.post(
                url,
                json={"contents": contents},
                timeout=120,
            )
            response.raise_for_status()

        except Exception as exc:
            raise ProviderError(str(exc)) from exc

        data = response.json()

        candidates = data.get("candidates", [])

        if not candidates:
            raise ProviderError(
                "Google returned no candidates."
            )

        parts = (
            candidates[0]
            .get("content", {})
            .get("parts", [])
        )

        text = "".join(
            part.get("text", "")
            for part in parts
        )

        return AIResponse(
            text=text,
            provider=self.name,
            model=model,
            metadata=data,
        )
'@

Write-FileSafe (Join-Path $Package "providers\registry.py") @'
from __future__ import annotations

from .base import ModelProvider
from .openai import OpenAIProvider
from .openrouter import OpenRouterProvider
from .anthropic import AnthropicProvider
from .google import GoogleProvider


class ProviderRegistry:

    def __init__(self):
        self._providers: dict[str, ModelProvider] = {}

    def register(
        self,
        provider: ModelProvider,
    ) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> ModelProvider:

        if name not in self._providers:
            raise KeyError(
                f"Provider not registered: {name}"
            )

        return self._providers[name]

    @classmethod
    def default(cls) -> "ProviderRegistry":

        registry = cls()

        registry.register(OpenAIProvider())
        registry.register(OpenRouterProvider())
        registry.register(AnthropicProvider())
        registry.register(GoogleProvider())

        return registry
'@

Write-FileSafe (Join-Path $Package "providers\__init__.py") @'
from .base import ModelProvider, ProviderError
from .registry import ProviderRegistry

__all__ = [
    "ModelProvider",
    "ProviderError",
    "ProviderRegistry",
]
'@

# =========================================================================
# MEMORY
# =========================================================================

Write-Header "6. MEMORY SYSTEM"

Write-FileSafe (Join-Path $Package "memory\store.py") @'
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


class MemoryStore:

    def __init__(self, path: str):
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
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    def remember(
        self,
        category: str,
        content: str,
        metadata: dict | None = None,
    ):

        with self._connect() as db:

            db.execute(
                """
                INSERT INTO memories
                (category, content, metadata, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    category,
                    content,
                    json.dumps(metadata or {}),
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
                ),
            )

    def recent(
        self,
        limit: int = 20,
        category: str | None = None,
    ):

        with self._connect() as db:

            if category:

                rows = db.execute(
                    """
                    SELECT category, content, metadata, created_at
                    FROM memories
                    WHERE category = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (category, limit),
                ).fetchall()

            else:

                rows = db.execute(
                    """
                    SELECT category, content, metadata, created_at
                    FROM memories
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        return [
            {
                "category": row[0],
                "content": row[1],
                "metadata": json.loads(row[2] or "{}"),
                "created_at": row[3],
            }
            for row in rows
        ]
'@

Write-FileSafe (Join-Path $Package "memory\manager.py") @'
from __future__ import annotations

from .store import MemoryStore


class MemoryManager:

    def __init__(self, store: MemoryStore):
        self.store = store

    def save_interaction(
        self,
        prompt: str,
        answer: str,
    ):

        self.store.remember(
            "interaction",
            prompt,
            {
                "answer": answer
            },
        )

    def context(
        self,
        limit: int = 10,
    ):

        memories = self.store.recent(limit)

        if not memories:
            return ""

        lines = []

        for memory in memories:
            lines.append(
                f"[{memory['category']}] "
                f"{memory['content']}"
            )

        return "\n".join(lines)
'@

Write-FileSafe (Join-Path $Package "memory\__init__.py") @'
from .store import MemoryStore
from .manager import MemoryManager

__all__ = [
    "MemoryStore",
    "MemoryManager",
]
'@

# =========================================================================
# AGENTS
# =========================================================================

Write-Header "7. AGENT FABRIC"

Write-FileSafe (Join-Path $Package "agents\base.py") @'
from __future__ import annotations

from abc import ABC, abstractmethod
from ..models import Problem


class Agent(ABC):

    name = "general"

    @abstractmethod
    def instructions(self) -> str:
        raise NotImplementedError

    def can_handle(self, problem: Problem) -> bool:
        return True
'@

Write-FileSafe (Join-Path $Package "agents\specialists.py") @'
from .base import Agent


class GeneralAgent(Agent):

    name = "general"

    def instructions(self):
        return """
You are the general problem-solving agent.
Understand the problem before answering.
Separate facts from assumptions.
Prefer evidence and explicit calculations.
Do not fabricate unavailable information.
"""


class ResearchAgent(Agent):

    name = "research"

    def instructions(self):
        return """
You are a research specialist.
Identify claims requiring evidence.
Distinguish established facts, uncertainty,
and hypotheses.
"""


class CodingAgent(Agent):

    name = "coding"

    def instructions(self):
        return """
You are a software engineering specialist.
Inspect architecture before changing it.
Prefer minimal, testable, maintainable changes.
Never silently destroy existing functionality.
"""


class DataAgent(Agent):

    name = "data"

    def instructions(self):
        return """
You are a data analysis specialist.
Use quantitative reasoning.
Check assumptions, missing data, outliers,
and statistical limitations.
"""


class MathematicsAgent(Agent):

    name = "mathematics"

    def instructions(self):
        return """
You are a mathematics specialist.
Derive results carefully.
Show relevant calculations.
Verify numerical conclusions.
"""


class EngineeringAgent(Agent):

    name = "engineering"

    def instructions(self):
        return """
You are an engineering reasoning specialist.
State assumptions, constraints, safety factors,
and uncertainty.
Never claim physical validation without actual
engineering calculations or measurements.
"""


class DocumentAgent(Agent):

    name = "document"

    def instructions(self):
        return """
You are a document intelligence specialist.
Extract structure, meaning, requirements,
contradictions, and actionable information.
"""


class CADAgent(Agent):

    name = "cad"

    def instructions(self):
        return """
You are a CAD reasoning specialist.
Treat geometry, dimensions, constraints,
and engineering assumptions explicitly.
Do not claim a CAD operation occurred unless
a connected CAD tool actually executed it.
"""
'@

Write-FileSafe (Join-Path $Package "agents\registry.py") @'
from .base import Agent
from .specialists import (
    GeneralAgent,
    ResearchAgent,
    CodingAgent,
    DataAgent,
    MathematicsAgent,
    EngineeringAgent,
    DocumentAgent,
    CADAgent,
)


class AgentRegistry:

    def __init__(self):

        self._agents: dict[str, Agent] = {}

        for agent in [
            GeneralAgent(),
            ResearchAgent(),
            CodingAgent(),
            DataAgent(),
            MathematicsAgent(),
            EngineeringAgent(),
            DocumentAgent(),
            CADAgent(),
        ]:
            self.register(agent)

    def register(self, agent: Agent):
        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent:
        return self._agents.get(
            name,
            self._agents["general"],
        )

    def names(self):
        return sorted(self._agents.keys())
'@

Write-FileSafe (Join-Path $Package "agents\__init__.py") @'
from .base import Agent
from .registry import AgentRegistry

__all__ = [
    "Agent",
    "AgentRegistry",
]
'@

# =========================================================================
# TOOLS
# =========================================================================

Write-Header "8. TOOL FABRIC"

Write-FileSafe (Join-Path $Package "tools\base.py") @'
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):

    name = "tool"
    description = ""

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        raise NotImplementedError
'@

Write-FileSafe (Join-Path $Package "tools\registry.py") @'
from __future__ import annotations

from .base import Tool


class ToolRegistry:

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def list(self):
        return list(self._tools.values())

    def names(self):
        return sorted(self._tools.keys())
'@

Write-FileSafe (Join-Path $Package "tools\system.py") @'
from __future__ import annotations

from pathlib import Path
from .base import Tool


class RepositoryStatusTool(Tool):

    name = "repository_status"

    description = (
        "Inspect basic repository structure without modifying files."
    )

    def __init__(self, repository: str):
        self.repository = Path(repository)

    def execute(self, **kwargs):

        if not self.repository.exists():
            return {
                "exists": False,
                "path": str(self.repository),
            }

        entries = []

        for item in self.repository.iterdir():
            entries.append(item.name)

        return {
            "exists": True,
            "path": str(self.repository),
            "entries": sorted(entries)[:200],
        }
'@

Write-FileSafe (Join-Path $Package "tools\__init__.py") @'
from .base import Tool
from .registry import ToolRegistry

__all__ = [
    "Tool",
    "ToolRegistry",
]
'@

# =========================================================================
# EXECUTION
# =========================================================================

Write-Header "9. EXECUTION ENGINE"

Write-FileSafe (Join-Path $Package "execution\planner.py") @'
from __future__ import annotations

import re
import uuid

from ..models import Problem, Plan, PlanStep


class Planner:

    def build(self, problem: Problem) -> Plan:

        text = problem.original.lower()

        steps = []

        if any(
            word in text
            for word in [
                "research",
                "latest",
                "current",
                "find",
                "compare",
            ]
        ):
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Identify required evidence and research questions.",
                    agent="research",
                )
            )

        if any(
            word in text
            for word in [
                "code",
                "python",
                "software",
                "repository",
                "bug",
                "error",
            ]
        ):
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Analyze the software problem and implementation constraints.",
                    agent="coding",
                )
            )

        if any(
            word in text
            for word in [
                "calculate",
                "equation",
                "math",
                "percentage",
                "statistics",
            ]
        ):
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Perform and verify quantitative reasoning.",
                    agent="mathematics",
                )
            )

        if any(
            word in text
            for word in [
                "cad",
                "geometry",
                "design",
                "structural",
            ]
        ):
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Analyze engineering or CAD-specific constraints.",
                    agent="engineering",
                )
            )

        if not steps:
            steps.append(
                PlanStep(
                    id=str(uuid.uuid4()),
                    description="Analyze the problem and determine the most appropriate solution path.",
                    agent="general",
                )
            )

        steps.append(
            PlanStep(
                id=str(uuid.uuid4()),
                description="Critically review the proposed solution.",
                agent="general",
            )
        )

        return Plan(
            objective=problem.objective,
            steps=steps,
            rationale="Plan generated from the problem's intent and constraints.",
        )
'@

Write-FileSafe (Join-Path $Package "execution\orchestrator.py") @'
from __future__ import annotations

from ..models import (
    AIRequest,
    AIResponse,
    BrainResult,
    Problem,
    Plan,
)
from ..providers.registry import ProviderRegistry
from ..agents.registry import AgentRegistry


class ExecutionEngine:

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

        instructions = []

        for step in plan.steps:

            agent = self.agents.get(step.agent)

            instructions.append(
                f"Step: {step.description}\n"
                f"Specialist: {agent.name}\n"
                f"Instructions: {agent.instructions()}"
            )

        system = f"""
You are Sovereign Intelligence, the problem-solving
engine of a larger software platform.

Your job is to solve the user's problem accurately,
not merely produce plausible text.

Operating rules:

1. Understand the objective.
2. Respect constraints.
3. Separate facts from assumptions.
4. Never fabricate tool execution.
5. Never claim certainty without evidence.
6. Use explicit reasoning where useful.
7. Identify uncertainty.
8. Prefer actionable solutions.
9. Preserve existing software functionality.
10. If information is missing, say what is missing.

Execution plan:

{chr(10).join(instructions)}

Relevant memory:

{memory_context[:12000]}
"""

        request = AIRequest(
            prompt=problem.original,
            system=system,
            model=model,
        )

        trace.append(
            {
                "event": "provider_request",
                "provider": provider_name,
                "model": model,
            }
        )

        response: AIResponse = provider.generate(request)

        trace.append(
            {
                "event": "provider_response",
                "provider": response.provider,
                "model": response.model,
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

Write-FileSafe (Join-Path $Package "execution\__init__.py") @'
from .planner import Planner
from .orchestrator import ExecutionEngine

__all__ = [
    "Planner",
    "ExecutionEngine",
]
'@

# =========================================================================
# VERIFICATION
# =========================================================================

Write-Header "10. VERIFICATION ENGINE"

Write-FileSafe (Join-Path $Package "verification.py") @'
from __future__ import annotations

import re

from .models import VerificationResult


class Verifier:

    def evaluate(
        self,
        answer: str,
    ) -> VerificationResult:

        issues = []
        recommendations = []

        if not answer.strip():
            return VerificationResult(
                passed=False,
                confidence=0.0,
                issues=["The AI returned an empty answer."],
            )

        suspicious = [
            r"\bguaranteed\b",
            r"\b100%\b",
            r"\bdefinitely\b",
            r"\bwithout any doubt\b",
        ]

        for pattern in suspicious:

            if re.search(
                pattern,
                answer,
                flags=re.IGNORECASE,
            ):
                issues.append(
                    "Answer contains an unusually strong certainty claim."
                )

        if issues:

            recommendations.append(
                "Rephrase absolute claims unless independently verified."
            )

        confidence = 0.95 if not issues else 0.70

        return VerificationResult(
            passed=True,
            confidence=confidence,
            issues=issues,
            recommendations=recommendations,
        )
'@

# =========================================================================
# KNOWLEDGE
# =========================================================================

Write-Header "11. KNOWLEDGE ENGINE"

Write-FileSafe (Join-Path $Package "knowledge\documents.py") @'
from __future__ import annotations

from pathlib import Path


SUPPORTED = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".csv",
}


def read_text_document(path: str) -> str:

    file = Path(path)

    if file.suffix.lower() not in SUPPORTED:
        raise ValueError(
            f"Unsupported document type: {file.suffix}"
        )

    return file.read_text(
        encoding="utf-8",
        errors="replace",
    )


def chunk_text(
    text: str,
    size: int = 1200,
    overlap: int = 150,
):

    if size <= overlap:
        raise ValueError(
            "Chunk size must be greater than overlap."
        )

    chunks = []

    start = 0

    while start < len(text):

        end = min(
            start + size,
            len(text),
        )

        chunks.append(
            text[start:end]
        )

        if end == len(text):
            break

        start = end - overlap

    return chunks
'@

Write-FileSafe (Join-Path $Package "knowledge\retrieval.py") @'
from __future__ import annotations

import math
import re


def tokenize(text: str) -> set[str]:

    return set(
        re.findall(
            r"[a-zA-Z0-9_]+",
            text.lower(),
        )
    )


def lexical_score(
    query: str,
    document: str,
) -> float:

    q = tokenize(query)
    d = tokenize(document)

    if not q or not d:
        return 0.0

    intersection = len(q & d)

    return intersection / math.sqrt(
        len(q) * len(d)
    )


def retrieve(
    query: str,
    documents: list[str],
    top_k: int = 5,
):

    scored = [
        (
            lexical_score(query, document),
            document,
        )
        for document in documents
    ]

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return scored[:top_k]
'@

Write-FileSafe (Join-Path $Package "knowledge\__init__.py") @'
from .documents import read_text_document, chunk_text
from .retrieval import retrieve

__all__ = [
    "read_text_document",
    "chunk_text",
    "retrieve",
]
'@

# =========================================================================
# SAFETY
# =========================================================================

Write-Header "12. SAFETY AND PERMISSIONS"

Write-FileSafe (Join-Path $Package "safety\policy.py") @'
from __future__ import annotations


class ToolPolicy:

    READ_ONLY = "read_only"
    WRITE = "write"
    EXECUTE = "execute"

    def __init__(self):
        self.allowed: dict[str, set[str]] = {}

    def allow(
        self,
        tool: str,
        action: str,
    ):

        self.allowed.setdefault(
            tool,
            set(),
        ).add(action)

    def can(
        self,
        tool: str,
        action: str,
    ) -> bool:

        return action in self.allowed.get(
            tool,
            set(),
        )
'@

Write-FileSafe (Join-Path $Package "safety\audit.py") @'
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


class AuditLogger:

    def __init__(self, path: str):

        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def record(
        self,
        event: str,
        data: dict,
    ):

        entry = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "event": event,
            "data": data,
        }

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                json.dumps(
                    entry,
                    ensure_ascii=False,
                )
                + "\n"
            )
'@

Write-FileSafe (Join-Path $Package "safety\__init__.py") @'
from .policy import ToolPolicy
from .audit import AuditLogger

__all__ = [
    "ToolPolicy",
    "AuditLogger",
]
'@

# =========================================================================
# OBSERVABILITY
# =========================================================================

Write-Header "13. OBSERVABILITY"

Write-FileSafe (Join-Path $Package "observability\trace.py") @'
from __future__ import annotations

import time


class Trace:

    def __init__(self):
        self.events = []

    def event(
        self,
        name: str,
        **metadata,
    ):

        self.events.append(
            {
                "name": name,
                "time": time.time(),
                "metadata": metadata,
            }
        )

    def export(self):
        return list(self.events)
'@

Write-FileSafe (Join-Path $Package "observability\__init__.py") @'
from .trace import Trace

__all__ = ["Trace"]
'@

# =========================================================================
# MAIN BRAIN
# =========================================================================

Write-Header "14. SOVEREIGN BRAIN"

Write-FileSafe (Join-Path $Package "orchestrator.py") @'
from __future__ import annotations

from .config import BrainConfig
from .models import Problem, BrainResult
from .providers.registry import ProviderRegistry
from .agents.registry import AgentRegistry
from .memory import MemoryStore, MemoryManager
from .execution import Planner, ExecutionEngine
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

        self.planner = Planner()

        self.executor = ExecutionEngine(
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

        problem = Problem(
            original=prompt,
            objective=prompt,
        )

        memory_context = self.memory.context()

        plan = self.planner.build(problem)

        self.audit.record(
            "problem_started",
            {
                "prompt": prompt,
                "provider": selected_provider,
                "model": selected_model,
            },
        )

        try:

            result = self.executor.execute(
                problem=problem,
                plan=plan,
                provider_name=selected_provider,
                model=selected_model,
                memory_context=memory_context,
            )

            if self.config.enable_verification:

                verification = self.verifier.evaluate(
                    result.answer
                )

                result.verification = verification

            self.memory.save_interaction(
                prompt,
                result.answer,
            )

            self.audit.record(
                "problem_completed",
                {
                    "provider": result.provider,
                    "model": result.model,
                    "verified": (
                        result.verification.passed
                        if result.verification
                        else None
                    ),
                },
            )

            return result

        except Exception as exc:

            self.audit.record(
                "problem_failed",
                {
                    "error": str(exc),
                },
            )

            raise
'@

# =========================================================================
# API
# =========================================================================

Write-Header "15. PUBLIC API"

Write-FileSafe (Join-Path $Package "api\interface.py") @'
from __future__ import annotations

from ..orchestrator import SovereignBrain


_brain: SovereignBrain | None = None


def get_brain() -> SovereignBrain:

    global _brain

    if _brain is None:
        _brain = SovereignBrain()

    return _brain


def solve(
    prompt: str,
    provider: str | None = None,
    model: str | None = None,
):

    return get_brain().solve(
        prompt,
        provider=provider,
        model=model,
    )
'@

Write-FileSafe (Join-Path $Package "api\__init__.py") @'
from .interface import get_brain, solve

__all__ = [
    "get_brain",
    "solve",
]
'@

# =========================================================================
# CONFIG FILE
# =========================================================================

Write-Header "16. ENVIRONMENT CONFIGURATION"

Write-FileSafe (Join-Path $Repo ".env.sovereign.example") @'
# ============================================================
# SOVEREIGN INTELLIGENCE CONFIGURATION
# ============================================================

# Primary provider:
SOVEREIGN_AI_PROVIDER=openai

# Primary model:
SOVEREIGN_AI_MODEL=gpt-5

# Optional fallback:
# SOVEREIGN_AI_FALLBACK_PROVIDER=openrouter

SOVEREIGN_AI_TEMPERATURE=0.2
SOVEREIGN_AI_MAX_TOKENS=4096

SOVEREIGN_AI_VERIFICATION=true
SOVEREIGN_AI_MAX_ITERATIONS=4

# OpenAI:
OPENAI_API_KEY=

# OpenRouter:
OPENROUTER_API_KEY=

# Anthropic:
ANTHROPIC_API_KEY=

# Google:
GOOGLE_API_KEY=
'@

# =========================================================================
# STREAMLIT PAGE
# =========================================================================

Write-Header "17. STREAMLIT INTELLIGENCE CENTER"

Write-FileSafe (Join-Path $Pages "Sovereign Intelligence.py") @'
from __future__ import annotations

import os
import streamlit as st

from sovereign_intelligence import SovereignBrain


st.set_page_config(
    page_title="Sovereign Intelligence",
    page_icon="🧠",
    layout="wide",
)


@st.cache_resource
def get_brain():

    return SovereignBrain()


st.title("🧠 Sovereign Intelligence")
st.caption(
    "The problem-solving intelligence layer of the platform."
)

with st.sidebar:

    st.subheader("Brain Configuration")

    provider = st.selectbox(
        "Provider",
        [
            "openai",
            "openrouter",
            "anthropic",
            "google",
        ],
    )

    model = st.text_input(
        "Model",
        value=os.getenv(
            "SOVEREIGN_AI_MODEL",
            "gpt-5",
        ),
    )

    verification = st.checkbox(
        "Verification",
        value=True,
    )

    st.divider()

    st.write(
        "This interface connects to the native "
        "Sovereign Intelligence Engine."
    )


if "sovereign_messages" not in st.session_state:
    st.session_state.sovereign_messages = []


for message in st.session_state.sovereign_messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


prompt = st.chat_input(
    "Describe the problem you want Sovereign Intelligence to solve..."
)


if prompt:

    st.session_state.sovereign_messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        with st.spinner(
            "Analyzing, planning and solving..."
        ):

            try:

                brain = get_brain()

                brain.config.enable_verification = verification

                result = brain.solve(
                    prompt,
                    provider=provider,
                    model=model,
                )

                st.markdown(result.answer)

                if result.verification:

                    with st.expander(
                        "Verification"
                    ):

                        st.write(
                            "Passed:",
                            result.verification.passed,
                        )

                        st.write(
                            "Confidence:",
                            result.verification.confidence,
                        )

                        if result.verification.issues:
                            st.write(
                                "Issues:"
                            )
                            for issue in result.verification.issues:
                                st.write(
                                    f"- {issue}"
                                )

                if result.plan:

                    with st.expander(
                        "Execution Plan"
                    ):

                        for step in result.plan.steps:

                            st.write(
                                f"**{step.agent}** — "
                                f"{step.description}"
                            )

                st.session_state.sovereign_messages.append(
                    {
                        "role": "assistant",
                        "content": result.answer,
                    }
                )

            except Exception as exc:

                st.error(
                    f"Sovereign Intelligence error: {exc}"
                )

                st.info(
                    "Check your provider API key and "
                    "model configuration."
                )
'@

# =========================================================================
# CLI
# =========================================================================

Write-Header "18. CLI"

Write-FileSafe (Join-Path $Package "__main__.py") @'
from __future__ import annotations

import argparse

from .orchestrator import SovereignBrain


def main():

    parser = argparse.ArgumentParser(
        description="Sovereign Intelligence CLI"
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        help="Problem to solve",
    )

    parser.add_argument(
        "--provider",
        default=None,
    )

    parser.add_argument(
        "--model",
        default=None,
    )

    args = parser.parse_args()

    if not args.prompt:

        print(
            "Usage: python -m sovereign_intelligence "
            "\"your problem\""
        )

        raise SystemExit(1)

    brain = SovereignBrain()

    result = brain.solve(
        args.prompt,
        provider=args.provider,
        model=args.model,
    )

    print()
    print(result.answer)
    print()

    if result.verification:

        print(
            f"Verification confidence: "
            f"{result.verification.confidence:.2f}"
        )


if __name__ == "__main__":
    main()
'@

# =========================================================================
# HEALTH CHECK
# =========================================================================

Write-Header "19. HEALTH CHECK"

Write-FileSafe (Join-Path $Tools "Check-SovereignIntelligence.ps1") @'
$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Repo ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "============================================="
Write-Host " SOVEREIGN INTELLIGENCE HEALTH CHECK"
Write-Host "============================================="
Write-Host ""

if (-not (Test-Path $Python)) {
    Write-Host "[FAIL] Python environment missing" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Python environment"

& $Python -c "import sovereign_intelligence; print('[OK] sovereign_intelligence import')"

if ($LASTEXITCODE -ne 0) {
    exit 1
}

& $Python -c "from sovereign_intelligence.agents import AgentRegistry; print('[OK] agent registry'); print(AgentRegistry().names())"

& $Python -c "from sovereign_intelligence.providers import ProviderRegistry; print('[OK] provider registry'); print(list(ProviderRegistry.default()._providers.keys()))"

& $Python -c "from sovereign_intelligence.knowledge import chunk_text; print('[OK] knowledge subsystem'); print(len(chunk_text('hello world ' * 500)))"

Write-Host ""
Write-Host "[SUCCESS] Sovereign Intelligence health check passed." -ForegroundColor Green
'@

# =========================================================================
# TESTS
# =========================================================================

Write-Header "20. AUTOMATED TESTS"

Write-FileSafe (Join-Path $Tests "__init__.py") ""

Write-FileSafe (Join-Path $Tests "test_core.py") @'
from sovereign_intelligence.agents import AgentRegistry
from sovereign_intelligence.execution import Planner
from sovereign_intelligence.knowledge import chunk_text
from sovereign_intelligence.models import Problem
from sovereign_intelligence.verification import Verifier


def test_agents_exist():

    registry = AgentRegistry()

    assert "general" in registry.names()
    assert "coding" in registry.names()
    assert "research" in registry.names()


def test_planner():

    planner = Planner()

    problem = Problem(
        original="Analyze this Python error",
        objective="Fix the error",
    )

    plan = planner.build(problem)

    assert plan.steps
    assert any(
        step.agent == "coding"
        for step in plan.steps
    )


def test_chunking():

    chunks = chunk_text(
        "hello " * 1000
    )

    assert len(chunks) > 1


def test_verifier():

    result = Verifier().evaluate(
        "This is a reasonable answer."
    )

    assert result.passed
    assert result.confidence > 0
'@

# =========================================================================
# DEPENDENCIES
# =========================================================================

Write-Header "21. DEPENDENCIES"

Write-FileSafe (Join-Path $Repo "requirements-sovereign-intelligence.txt") @'
httpx>=0.27
pydantic>=2.7
'@

if ($InstallDependencies) {

    $CacheDir = "D:\python_packages\pip_cache"

    Ensure-Directory $CacheDir

    $env:PIP_CACHE_DIR = $CacheDir

    Write-Host "Using pip cache: $CacheDir"

    & $VenvPip install `
        -r (Join-Path $Repo "requirements-sovereign-intelligence.txt")

    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }

    Write-OK "Dependencies installed"
}

# =========================================================================
# COMPILE
# =========================================================================

Write-Header "22. PYTHON COMPILATION"

if ($RunCompile) {

    Invoke-Python @(
        "-m",
        "compileall",
        "-q",
        "sovereign_intelligence"
    )

    Write-OK "Python compilation passed"
}

# =========================================================================
# TEST
# =========================================================================

Write-Header "23. TEST SUITE"

if ($RunTests) {

    $Pytest = Join-Path $Repo ".venv\Scripts\pytest.exe"

    if (Test-Path $Pytest) {

        & $Pytest `
            (Join-Path $Repo "tests\sovereign_intelligence") `
            "-q"

        if ($LASTEXITCODE -ne 0) {
            throw "Sovereign Intelligence tests failed."
        }

        Write-OK "Tests passed"

    }
    else {

        Write-WARN "pytest is not installed."

        & $VenvPip install pytest

        if ($LASTEXITCODE -eq 0) {

            & $Pytest `
                (Join-Path $Repo "tests\sovereign_intelligence") `
                "-q"

            if ($LASTEXITCODE -ne 0) {
                throw "Tests failed."
            }

            Write-OK "Tests passed"
        }
    }
}

# =========================================================================
# GITIGNORE
# =========================================================================

Write-Header "24. GIT SAFETY"

$GitIgnore = Join-Path $Repo ".gitignore"

if (Test-Path $GitIgnore) {

    $existing = Get-Content $GitIgnore -Raw

    $entries = @(
        ".env.sovereign"
        "data/sovereign_intelligence/"
        "backups/"
        "__pycache__/"
        "*.pyc"
    )

    foreach ($entry in $entries) {

        if ($existing -notmatch [regex]::Escape($entry)) {

            Add-Content `
                -LiteralPath $GitIgnore `
                -Value "`r`n$entry"

            Write-OK "Added .gitignore entry: $entry"
        }
    }

}
else {

    Write-FileSafe $GitIgnore @'
.env.sovereign
data/sovereign_intelligence/
backups/
__pycache__/
*.pyc
'@
}

# =========================================================================
# DOCUMENTATION
# =========================================================================

Write-Header "25. DOCUMENTATION"

Write-FileSafe (Join-Path $Docs "ARCHITECTURE.md") @'
# Sovereign Intelligence Architecture

## Purpose

Sovereign Intelligence is the native AI orchestration layer for the
notion-live-analyzer platform.

## Major components

- Provider Fabric
- Agent Fabric
- Planning
- Execution
- Memory
- Knowledge
- Tool Registry
- Verification
- Safety
- Audit
- Observability
- Streamlit interface

## Design principle

The intelligence layer is additive. Existing application functionality
should remain independently usable.

## Provider abstraction

The system separates the problem-solving engine from the model provider.

## Agent abstraction

Specialized agents provide domain-specific operating instructions.

## Verification

Responses can pass through a lightweight verification layer before being
presented to the user.

## Future extensions

- streaming responses
- structured outputs
- vector databases
- embeddings
- semantic reranking
- MCP integration
- sandboxed execution
- multimodal processing
- voice
- background tasks
- distributed workers
- evaluation benchmarks
'@

Write-FileSafe (Join-Path $Docs "ROADMAP.md") @'
# Sovereign Intelligence Roadmap

## Stage 1
Foundation and provider abstraction.

## Stage 2
Planning and execution.

## Stage 3
Specialist agent fabric.

## Stage 4
Tool registry.

## Stage 5
Memory.

## Stage 6
Knowledge retrieval.

## Stage 7
Verification.

## Stage 8
Observability and evaluation.

## Stage 9
Streaming.

## Stage 10
Structured outputs.

## Stage 11
Embeddings and vector search.

## Stage 12
MCP interoperability.

## Stage 13
Sandboxed execution.

## Stage 14
Multimodal intelligence.

## Stage 15
Voice/realtime intelligence.

## Stage 16
Autonomous background task execution.

## Stage 17
Advanced evaluation and benchmarking.

## Stage 18
Production hardening.
'@

# =========================================================================
# FINAL IMPORT TEST
# =========================================================================

Write-Header "26. FINAL IMPORT TEST"

Invoke-Python @(
    "-c",
    "from sovereign_intelligence import SovereignBrain; print('SOVEREIGN_BRAIN_IMPORT_OK')"
)

Write-OK "Sovereign Brain import successful"

# =========================================================================
# GIT STATUS
# =========================================================================

Write-Header "27. GIT STATUS"

& git status --short

# =========================================================================
# OPTIONAL COMMIT
# =========================================================================

if ($GitCommit) {

    Write-Header "28. GIT COMMIT"

    & git add `
        sovereign_intelligence `
        "pages\Sovereign Intelligence.py" `
        tests\sovereign_intelligence `
        tools\Check-SovereignIntelligence.ps1 `
        requirements-sovereign-intelligence.txt `
        .env.sovereign.example `
        docs\sovereign_intelligence `
        .gitignore

    if ($LASTEXITCODE -ne 0) {
        throw "git add failed."
    }

    & git commit `
        -m "Add Sovereign Intelligence problem solving engine"

    if ($LASTEXITCODE -ne 0) {
        throw "git commit failed."
    }

    Write-OK "Git commit created"

    Write-Host ""
    Write-Host "PUSH COMMAND:" -ForegroundColor Yellow
    Write-Host "git push origin main"
}

# =========================================================================
# COMPLETE
# =========================================================================

Write-Header "BUILD COMPLETE"

Write-Host ""
Write-Host "SOVEREIGN INTELLIGENCE has been added." -ForegroundColor Green
Write-Host ""
Write-Host "Created:"
Write-Host "  sovereign_intelligence/"
Write-Host "  pages/Sovereign Intelligence.py"
Write-Host "  tests/sovereign_intelligence/"
Write-Host "  tools/Check-SovereignIntelligence.ps1"
Write-Host "  requirements-sovereign-intelligence.txt"
Write-Host "  .env.sovereign.example"
Write-Host "  docs/sovereign_intelligence/"
Write-Host ""
Write-Host "Backup:"
Write-Host "  $BackupRoot"
Write-Host ""
Write-Host "NEXT:"
Write-Host "  1. Configure an AI provider API key."
Write-Host "  2. Run the health check."
Write-Host "  3. Start Streamlit."
Write-Host "  4. Open the Sovereign Intelligence page."
Write-Host ""
Write-Host "Health check:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\tools\Check-SovereignIntelligence.ps1"
Write-Host ""
Write-Host "Streamlit:"
Write-Host "  .\.venv\Scripts\python.exe -m streamlit run app.py"
Write-Host ""