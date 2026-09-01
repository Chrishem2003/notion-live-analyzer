from __future__ import annotations

import json
from pathlib import Path

from .run_models import IntelligenceRun


class RunRecorder:

    def __init__(
        self,
        path: str = "data/intelligence_runs.jsonl",
    ):

        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def record(
        self,
        run: IntelligenceRun,
    ):

        payload = {
            "id": run.id,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "status": run.status,
            "error": run.error,
            "metadata": run.metadata,
            "events": [
                {
                    "name": event.name,
                    "status": event.status,
                    "timestamp": event.timestamp,
                    "data": event.data,
                }
                for event in run.events
            ],
        }

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as handle:

            handle.write(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )

    def read_recent(
        self,
        limit: int = 20,
    ):

        if not self.path.exists():
            return []

        lines = self.path.read_text(
            encoding="utf-8"
        ).splitlines()

        records = []

        for line in lines[-limit:]:

            if not line.strip():
                continue

            records.append(
                json.loads(line)
            )

        return records
