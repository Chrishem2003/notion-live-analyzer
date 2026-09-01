from __future__ import annotations

from dataclasses import dataclass
import re

from .registry import ToolRegistry


@dataclass(frozen=True)
class ToolCandidate:

    name: str
    score: float
    reason: str


class ToolSelector:

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def select(
        self,
        problem: str,
        limit: int = 5,
    ) -> list[ToolCandidate]:

        problem = (problem or "").strip().lower()

        if not problem:
            return []

        candidates = []

        for tool in self.registry.list():

            name = tool.name.lower()
            description = (
                getattr(tool, "description", "")
                or ""
            ).lower()

            score = 0.0
            reasons = []

            terms = set(
                re.findall(
                    r"[a-z0-9_]+",
                    problem,
                )
            )

            searchable = set(
                re.findall(
                    r"[a-z0-9_]+",
                    name + " " + description,
                )
            )

            overlap = terms & searchable

            if overlap:
                score += min(
                    len(overlap) * 2.0,
                    8.0,
                )

                reasons.append(
                    "keyword relevance"
                )

            if name.replace("_", " ") in problem:
                score += 5.0
                reasons.append(
                    "tool name match"
                )

            if score > 0:

                candidates.append(
                    ToolCandidate(
                        name=tool.name,
                        score=score,
                        reason=", ".join(reasons),
                    )
                )

        candidates.sort(
            key=lambda item: (
                -item.score,
                item.name,
            )
        )

        return candidates[:limit]
