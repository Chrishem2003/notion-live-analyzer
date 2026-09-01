from __future__ import annotations

import time


class Trace:

    def __init__(self):
        self.events = []

    def event(
        self,
        name: str,
        **metadata,
    ):

        self.events.append(
            {
                "name": name,
                "time": time.time(),
                "metadata": metadata,
            }
        )

    def export(self):
        return list(self.events)