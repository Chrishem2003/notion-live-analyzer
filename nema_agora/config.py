"""Deployment configuration for the NEMA-AGORA persistence gate."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping


def _section(secrets: Mapping[str, object]) -> Mapping[str, object]:
    value = secrets.get("nema_agora", {})
    return value if isinstance(value, Mapping) else {}


def mode_from_secrets(secrets: Mapping[str, object]) -> str:
    """Return demo or persistent; unknown values fail closed to demo."""
    mode = _section(secrets).get("mode", "demo")
    return mode.strip().lower() if isinstance(mode, str) and mode.strip().lower() in {"demo", "persistent"} else "demo"


def database_path_from_secrets(secrets: Mapping[str, object]) -> Path | None:
    """Return an explicitly configured SQLite path; never invent a production path."""
    value = _section(secrets).get("database_path")
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(value).expanduser()
