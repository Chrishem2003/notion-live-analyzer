from __future__ import annotations

from pathlib import Path
from .base import Tool


class RepositoryStatusTool(Tool):

    name = "repository_status"

    description = (
        "Inspect basic repository structure without modifying files."
    )

    def __init__(self, repository: str):
        self.repository = Path(repository)

    def execute(self, **kwargs):

        if not self.repository.exists():
            return {
                "exists": False,
                "path": str(self.repository),
            }

        entries = []

        for item in self.repository.iterdir():
            entries.append(item.name)

        return {
            "exists": True,
            "path": str(self.repository),
            "entries": sorted(entries)[:200],
        }