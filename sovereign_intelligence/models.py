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