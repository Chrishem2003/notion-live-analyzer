from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProjectFile:
    version: str = "1.0"
    name: str = "Untitled SovereignCAD Project"
    metadata: dict[str, Any] = field(default_factory=dict)
    document: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "SovereignCAD",
            "version": self.version,
            "name": self.name,
            "metadata": dict(self.metadata),
            "document": dict(self.document),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectFile":
        if not isinstance(data, dict):
            raise TypeError("Project data must be a dictionary.")

        return cls(
            version=str(data.get("version", "1.0")),
            name=str(data.get("name", "Untitled SovereignCAD Project")),
            metadata=dict(data.get("metadata", {})),
            document=dict(data.get("document", {})),
        )