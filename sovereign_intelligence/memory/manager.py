from __future__ import annotations

from .store import MemoryStore


class MemoryManager:

    def __init__(self, store: MemoryStore):
        self.store = store

    def save_interaction(
        self,
        prompt: str,
        answer: str,
    ):

        self.store.remember(
            "interaction",
            prompt,
            {
                "answer": answer
            },
        )

    def context(
        self,
        limit: int = 10,
    ):

        memories = self.store.recent(limit)

        if not memories:
            return ""

        lines = []

        for memory in memories:
            lines.append(
                f"[{memory['category']}] "
                f"{memory['content']}"
            )

        return "\n".join(lines)