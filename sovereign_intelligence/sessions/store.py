from __future__ import annotations

import json
from pathlib import Path

from .models import IntelligenceSession


class SessionStore:

    def __init__(
        self,
        directory: str = "data/intelligence_sessions",
    ):

        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _path(self, session_id: str) -> Path:

        return self.directory / (
            f"{session_id}.json"
        )

    def save(
        self,
        session: IntelligenceSession,
    ):

        path = self._path(session.id)

        payload = {
            "id": session.id,
            "created_at": session.created_at,
            "events": session.events,
            "metadata": session.metadata,
        }

        path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return path

    def load(
        self,
        session_id: str,
    ) -> IntelligenceSession:

        path = self._path(session_id)

        if not path.exists():
            raise FileNotFoundError(
                f"Session not found: {session_id}"
            )

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        return IntelligenceSession(
            id=payload["id"],
            created_at=payload["created_at"],
            events=payload.get(
                "events",
                [],
            ),
            metadata=payload.get(
                "metadata",
                {},
            ),
        )

    def exists(
        self,
        session_id: str,
    ) -> bool:

        return self._path(
            session_id
        ).exists()

    def delete(
        self,
        session_id: str,
    ) -> bool:

        path = self._path(session_id)

        if not path.exists():
            return False

        path.unlink()

        return True
