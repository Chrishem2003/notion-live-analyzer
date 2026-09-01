from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievalCandidate:

    id: str

    content: str

    lexical_score: float = 0.0

    semantic_score: float = 0.0

    fused_score: float = 0.0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class RetrievalResult:

    query: str

    candidates: list[RetrievalCandidate]

    strategy: str = "hybrid"

    metadata: dict[str, Any] = field(
        default_factory=dict
    )
