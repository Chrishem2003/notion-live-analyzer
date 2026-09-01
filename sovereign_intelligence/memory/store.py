from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


class MemoryStore:

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _initialize(self):

        with self._connect() as db:

            db.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    def remember(
        self,
        category: str,
        content: str,
        metadata: dict | None = None,
    ):

        with self._connect() as db:

            db.execute(
                """
                INSERT INTO memories
                (category, content, metadata, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    category,
                    content,
                    json.dumps(metadata or {}),
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
                ),
            )

    def recent(
        self,
        limit: int = 20,
        category: str | None = None,
    ):

        with self._connect() as db:

            if category:

                rows = db.execute(
                    """
                    SELECT category, content, metadata, created_at
                    FROM memories
                    WHERE category = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (category, limit),
                ).fetchall()

            else:

                rows = db.execute(
                    """
                    SELECT category, content, metadata, created_at
                    FROM memories
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        return [
            {
                "category": row[0],
                "content": row[1],
                "metadata": json.loads(row[2] or "{}"),
                "created_at": row[3],
            }
            for row in rows
        ]