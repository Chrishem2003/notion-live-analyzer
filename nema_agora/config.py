"""Deployment configuration for NEMA-AGORA persistence and operations."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping


def _section(secrets: Mapping[str, object]) -> Mapping[str, object]:
    value = secrets.get("nema_agora", {})
    return value if isinstance(value, Mapping) else {}


def mode_from_secrets(secrets: Mapping[str, object]) -> str:
    """Return demo/persistent only for explicit valid configuration.

    An absent mode preserves the safe first-run demo experience. A present but
    malformed or unknown mode returns "invalid" so the UI can stop visibly
    rather than silently pretending an operator's configuration was accepted.
    """
    raw_section = secrets.get("nema_agora", {})
    if not isinstance(raw_section, Mapping):
        return "invalid"
    section = raw_section
    if "mode" not in section:
        return "demo"
    mode = section.get("mode")
    if isinstance(mode, str):
        normalized = mode.strip().lower()
        if normalized in {"demo", "persistent"}:
            return normalized
    return "invalid"


def database_path_from_secrets(secrets: Mapping[str, object]) -> Path | None:
    value = _section(secrets).get("database_path")
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(value).expanduser()


def backup_dir_from_secrets(secrets: Mapping[str, object]) -> Path | None:
    value = _section(secrets).get("backup_dir")
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(value).expanduser()


def backup_retention_from_secrets(secrets: Mapping[str, object]) -> int | None:
    value = _section(secrets).get("backup_retention", 7)
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if 1 <= value <= 3650 else None
