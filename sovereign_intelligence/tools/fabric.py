from __future__ import annotations

from .base import Tool
from .registry import ToolRegistry
from .system import RepositoryStatusTool

from .permissions import (
    PermissionGate,
    ToolPermissions,
)

from .audit import ToolAudit


class ToolFabric:

    def __init__(
        self,
        repository: str,
        audit_path: str = "data/tool_audit.jsonl",
    ):

        self.registry = ToolRegistry()

        self.permission_gate = PermissionGate(
            allow_read=True,
            allow_write=False,
            allow_execute=False,
            allow_network=False,
            allow_destructive=False,
        )

        self.audit = ToolAudit(
            audit_path
        )

        self._permissions = {}

        self.register(
            RepositoryStatusTool(repository),
            ToolPermissions(
                read=True
            ),
        )

    def register(
        self,
        tool: Tool,
        permissions: ToolPermissions,
    ):

        self.registry.register(tool)

        self._permissions[
            tool.name
        ] = permissions

    def available_tools(self):

        return self.registry.names()

    def execute(
        self,
        name: str,
        **kwargs,
    ):

        if name not in self._permissions:

            return {
                "success": False,
                "tool": name,
                "error": "Unknown tool.",
            }

        tool = self.registry.get(name)

        permissions = self._permissions[
            name
        ]

        decision = self.permission_gate.check(
            permissions
        )

        self.audit.record(
            "permission_check",
            {
                "tool": name,
                "allowed": decision.allowed,
                "reason": decision.reason,
            },
        )

        if not decision.allowed:

            return {
                "success": False,
                "tool": name,
                "error": decision.reason,
            }

        try:

            result = tool.execute(
                **kwargs
            )

            self.audit.record(
                "tool_execution",
                {
                    "tool": name,
                    "success": True,
                },
            )

            return {
                "success": True,
                "tool": name,
                "result": result,
            }

        except Exception as exc:

            self.audit.record(
                "tool_execution",
                {
                    "tool": name,
                    "success": False,
                    "error": str(exc),
                },
            )

            return {
                "success": False,
                "tool": name,
                "error": str(exc),
            }
