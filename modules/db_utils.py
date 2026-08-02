"""
Database utilities — shared SQLite connection handling for the local stores
used by the literature, audit, provenance, pipeline, and feed modules.
"""
import sqlite3
from pathlib import Path
from typing import Union


def connect_sqlite(db_path: Union[str, Path], foreign_keys: bool = False) -> sqlite3.Connection:
    """Open a WAL-mode connection with row factory for dict-like access."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    if foreign_keys:
        conn.execute("PRAGMA foreign_keys=ON")
    return conn
