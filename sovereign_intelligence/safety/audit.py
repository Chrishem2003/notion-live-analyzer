from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


class AuditLogger:

    def __init__(self, path: str):

        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def record(
        self,
        event: str,
        data: dict,
    ):

        entry = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "event": event,
            "data": data,
        }

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                json.dumps(
                    entry,
                    ensure_ascii=False,
                )
                + "\n"
            )