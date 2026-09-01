from __future__ import annotations

from .base import Tool
from .specs import ToolSpec


class ToolRegistry:

    def __init__(self):

        self._tools: dict[str, Tool] = {}

    def register(
        self,
        tool: Tool,
    ):

        if not tool.name:
            raise ValueError(
                "Tool name cannot be empty."
            )

        if tool.name in self._tools:
            raise ValueError(
                f"Tool already registered: {tool.name}"
            )

        self._tools[tool.name] = tool

    def unregister(
        self,
        name: str,
    ):

        self._tools.pop(
            name,
            None,
        )

    def get(
        self,
        name: str,
    ) -> Tool:

        if name not in self._tools:
            raise KeyError(
                f"Unknown tool: {name}"
            )

        return self._tools[name]

    def has(
        self,
        name: str,
    ) -> bool:

        return name in self._tools

    def list(self):

        return list(
            self._tools.values()
        )

    def names(self):

        return sorted(
            self._tools.keys()
        )

    def describe(self):

        descriptions = []

        for tool in self.list():

            permissions = getattr(
                tool,
                "permissions",
                None,
            )

            descriptions.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "permissions": permissions,
                }
            )

        return descriptions
