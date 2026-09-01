from __future__ import annotations

from .fabric import ToolFabric
from .selector import ToolSelector


class ToolReasoner:

    def __init__(
        self,
        fabric: ToolFabric,
    ):

        self.fabric = fabric
        self.selector = ToolSelector(
            fabric.registry
        )

    def discover(
        self,
        problem: str,
        limit: int = 5,
    ):

        candidates = self.selector.select(
            problem,
            limit=limit,
        )

        return [
            {
                "tool": candidate.name,
                "score": candidate.score,
                "reason": candidate.reason,
            }
            for candidate in candidates
        ]

    def execute_best(
        self,
        problem: str,
        **kwargs,
    ):

        candidates = self.selector.select(
            problem,
            limit=1,
        )

        if not candidates:

            return {
                "success": False,
                "error": "No suitable tool found.",
                "problem": problem,
            }

        selected = candidates[0]

        result = self.fabric.execute(
            selected.name,
            **kwargs,
        )

        return {
            "selection": {
                "tool": selected.name,
                "score": selected.score,
                "reason": selected.reason,
            },
            "result": result,
        }
