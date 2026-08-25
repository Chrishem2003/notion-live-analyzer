from __future__ import annotations

import json
from typing import Any

from .model import ProjectFile


class ProjectSerializer:

    @staticmethod
    def dumps(project: ProjectFile, *, indent: int = 2) -> str:
        if not isinstance(project, ProjectFile):
            raise TypeError("project must be a ProjectFile.")

        return json.dumps(
            project.to_dict(),
            indent=indent,
            ensure_ascii=False,
            sort_keys=True,
        )

    @staticmethod
    def loads(text: str) -> ProjectFile:
        if not isinstance(text, str):
            raise TypeError("Project data must be text.")

        data: Any = json.loads(text)

        if not isinstance(data, dict):
            raise ValueError("Project JSON root must be an object.")

        if data.get("format") != "SovereignCAD":
            raise ValueError("Invalid SovereignCAD project format.")

        return ProjectFile.from_dict(data)

    @staticmethod
    def dump_file(project: ProjectFile, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(ProjectSerializer.dumps(project))

    @staticmethod
    def load_file(path: str) -> ProjectFile:
        with open(path, "r", encoding="utf-8") as handle:
            return ProjectSerializer.loads(handle.read())