from __future__ import annotations

import uuid
from typing import Any

from .audit import ToolAudit
from .permissions import (
    PermissionGate,
)
from .registry import ToolRegistry
from .specs import (
    ToolRequest,
    ToolResult,
)


class ToolExecutor:

    def __init__(
        self,
        registry: ToolRegistry,
        permission_gate: PermissionGate | None = None,
        audit: ToolAudit | None = None,
    ):

        self.registry = registry

        self.permission_gate = (
            permission_gate
            or PermissionGate()
        )

        self.audit = (
            audit
            or ToolAudit()
        )

    def execute(
        self,
        request: ToolRequest,
    ) -> ToolResult:

        request_id = (
            request.request_id
            or str(uuid.uuid4())
        )

        self.audit.record(
            "tool_requested",
            {
                "request_id": request_id,
                "tool": request.tool,
                "arguments": request.arguments,
            },
        )

        try:

            tool = self.registry.get(
                request.tool
            )

        except KeyError as exc:

            result = ToolResult(
                tool=request.tool,
                success=False,
                error=str(exc),
                metadata={
                    "request_id": request_id,
                    "stage": "lookup",
                },
            )

            self.audit.record(
                "tool_failed",
                {
                    "request_id": request_id,
                    "tool": request.tool,
                    "error": str(exc),
                },
            )

            return result

        permissions = getattr(
            tool,
            "permissions",
            None,
        )

        if permissions is None:

            from .permissions import (
                ToolPermissions,
            )

            permissions = ToolPermissions(
                read=True
            )

        decision = (
            self.permission_gate.check(
                permissions
            )
        )

        if not decision.allowed:

            result = ToolResult(
                tool=request.tool,
                success=False,
                error=decision.reason,
                metadata={
                    "request_id": request_id,
                    "stage": "permission",
                },
            )

            self.audit.record(
                "tool_denied",
                {
                    "request_id": request_id,
                    "tool": request.tool,
                    "reason": decision.reason,
                },
            )

            return result

        try:

            output = tool.execute(
                **request.arguments
            )

            result = ToolResult(
                tool=request.tool,
                success=True,
                output=output,
                metadata={
                    "request_id": request_id,
                    "stage": "execution",
                },
            )

            self.audit.record(
                "tool_completed",
                {
                    "request_id": request_id,
                    "tool": request.tool,
                },
            )

            return result

        except Exception as exc:

            result = ToolResult(
                tool=request.tool,
                success=False,
                error=str(exc),
                metadata={
                    "request_id": request_id,
                    "stage": "execution",
                },
            )

            self.audit.record(
                "tool_failed",
                {
                    "request_id": request_id,
                    "tool": request.tool,
                    "error": str(exc),
                },
            )

            return result
