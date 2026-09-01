from __future__ import annotations

from pathlib import Path

from .documents import (
    SUPPORTED,
    chunk_text,
)
from .vector_index import (
    PersistentVectorIndex,
)


def index_directory(
    directory: str,
    index: PersistentVectorIndex,
    chunk_size: int = 1400,
    overlap: int = 180,
) -> int:

    root = Path(directory)

    if not root.exists():
        raise FileNotFoundError(
            str(root)
        )

    count = 0

    for path in root.rglob("*"):

        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED:
            continue

        if "__pycache__" in path.parts:
            continue

        try:

            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        except OSError:
            continue

        chunks = chunk_text(
            text,
            size=chunk_size,
            overlap=overlap,
        )

        for number, chunk in enumerate(
            chunks
        ):

            if not chunk.strip():
                continue

            relative = path.relative_to(
                root
            )

            index.add(
                content=chunk,
                metadata={
                    "source": str(relative),
                    "chunk": number,
                    "directory": str(root),
                },
                document_id=(
                    f"{relative}:{number}"
                ),
            )

            count += 1

    return count
