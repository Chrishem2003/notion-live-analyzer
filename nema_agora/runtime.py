"""Runtime construction helpers for the NEMA-AGORA pilot."""
from __future__ import annotations

from pathlib import Path

from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository


def initialize_persistent_service(database_path: str | Path) -> NemaAgoraService:
    """Initialize the configured persistent store without hiding startup errors.

    The Streamlit entrypoint presents a safe message and stops the run if this
    fails. It must not silently fall back to session-only demo storage after an
    operator explicitly selected persistent mode.
    """
    path = Path(database_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return NemaAgoraService(NemaAgoraRepository(path))
