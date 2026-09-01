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
