"""Curated page discovery for the Streamlit entrypoint.

NEMA-AGORA's specialist pages are retained as implementation/reference files but
must not be exposed as separate sidebar destinations. The consolidated workspace
is registered explicitly by app.py.
"""
from __future__ import annotations

import re
from pathlib import Path


def discover_other_pages(root: Path, pages_dir: Path) -> list[tuple[str, str]]:
    """Return visible non-NEMA page paths and labels in deterministic order."""
    if not pages_dir.is_dir():
        return []
    visible: list[tuple[str, str]] = []
    for page_path in sorted(pages_dir.glob("*.py")):
        if "NEMA_AGORA" in page_path.name.upper():
            continue
        stem = re.sub(r"^\d+_", "", page_path.stem)
        title = stem.replace("_", " ").strip() or page_path.stem
        visible.append((str(page_path.relative_to(root)), title))
    return visible
