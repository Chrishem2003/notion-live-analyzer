from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass
class IntelligenceSession:

    id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    created_at: str = field(
        default_factory=lambda:
        datetime.now(timezone.utc).isoformat()
    )

    events: list[dict[str, Any]] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def add_event(
        self,
        event: str,
        data: dict[str, Any] | None = None,
    ):

        self.events.append(
            {
                "event": event,
                "timestamp":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
                "data": data or {},
            }
        )
