from __future__ import annotations

from pathlib import Path


SUPPORTED = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".csv",
}


def read_text_document(path: str) -> str:

    file = Path(path)

    if file.suffix.lower() not in SUPPORTED:
        raise ValueError(
            f"Unsupported document type: {file.suffix}"
        )

    return file.read_text(
        encoding="utf-8",
        errors="replace",
    )


def chunk_text(
    text: str,
    size: int = 1200,
    overlap: int = 150,
):

    if size <= overlap:
        raise ValueError(
            "Chunk size must be greater than overlap."
        )

    chunks = []

    start = 0

    while start < len(text):

        end = min(
            start + size,
            len(text),
        )

        chunks.append(
            text[start:end]
        )

        if end == len(text):
            break

        start = end - overlap

    return chunks