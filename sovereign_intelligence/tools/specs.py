from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .permissions import ToolPermissions


@dataclass(frozen=True)
class ToolSpec:

    name: str

    description: str

    permissions: ToolPermissions = field(
        default_factory=ToolPermissions
    )

    input_schema: dict[str, Any] = field(
        default_factory=dict
    )

    category: str = "general"


@dataclass
class ToolResult:

    tool: str

    success: bool

    output: Any = None

    error: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class ToolRequest:

    tool: str

    arguments: dict[str, Any] = field(
        default_factory=dict
    )

    request_id: str | None = None
