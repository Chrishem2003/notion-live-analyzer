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