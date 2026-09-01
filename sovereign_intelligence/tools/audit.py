from datetime import datetime, timezone
from pathlib import Path
import json


class ToolAudit:

    def __init__(self, path="data/tool_audit.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event, data):

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "data": data,
        }

        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(record, default=str) + "\n"
            )
