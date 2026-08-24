from __future__ import annotations

from pathlib import Path

from .model import ProjectFile
from .serializer import ProjectSerializer


class ProjectPersistence:

    extension = ".scad"

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root is not None else Path.cwd()

    def save(
        self,
        project: ProjectFile,
        path: str | Path,
    ) -> Path:
        target = Path(path)

        if not target.is_absolute():
            target = self.root / target

        if target.suffix.lower() != self.extension:
            target = target.with_suffix(self.extension)

        target.parent.mkdir(parents=True, exist_ok=True)

        ProjectSerializer.dump_file(
            project,
            str(target),
        )

        return target

    def load(
        self,
        path: str | Path,
    ) -> ProjectFile:
        target = Path(path)

        if not target.is_absolute():
            target = self.root / target

        return ProjectSerializer.load_file(str(target))

    def exists(
        self,
        path: str | Path,
    ) -> bool:
        target = Path(path)

        if not target.is_absolute():
            target = self.root / target

        return target.exists()