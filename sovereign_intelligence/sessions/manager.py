from __future__ import annotations

from .models import IntelligenceSession
from .store import SessionStore


class SessionManager:

    def __init__(
        self,
        store: SessionStore | None = None,
    ):

        self.store = (
            store
            or SessionStore()
        )

    def create(
        self,
        metadata=None,
    ) -> IntelligenceSession:

        session = IntelligenceSession(
            metadata=metadata or {}
        )

        session.add_event(
            "session_created"
        )

        self.store.save(session)

        return session

    def record(
        self,
        session: IntelligenceSession,
        event: str,
        data=None,
    ):

        session.add_event(
            event,
            data,
        )

        self.store.save(session)

        return session

    def restore(
        self,
        session_id: str,
    ) -> IntelligenceSession:

        return self.store.load(
            session_id
        )
