"""Deployment configuration for NEMA-AGORA persistence and operations."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping


def _section(secrets: Mapping[str, object]) -> Mapping[str, object]:
    value = secrets.get("nema_agora", {})
    return value if isinstance(value, Mapping) else {}


def mode_from_secrets(secrets: Mapping[str, object]) -> str:
    mode = _section(secrets).get("mode", "demo")
    return mode.strip().lower() if isinstance(mode, str) and mode.strip().lower() in {"demo", "persistent"} else "demo"


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
    if isinstance(value, bool):
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if 1 <= value <= 3650 else None
