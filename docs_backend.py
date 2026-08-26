"""
docs_backend.py — Real collaborative editing, not last-write-wins.

Uses pycrdt (Python bindings for the same Rust `yrs` CRDT engine behind
Yjs, which is what powers real production collaborative editors — Jupyter
notebooks' RTC, for instance). Two people typing in different parts of the
same document at the same time get a mathematically guaranteed
conflict-free merge — this isn't "last save wins" with a lock, it's an
actual CRDT: the merge function is commutative and associative regardless
of what order updates arrive in.

Wire format: pycrdt's update bytes are Yjs-update-format compatible, so a
real Yjs client in the browser can apply updates this server produces, and
vice versa — same binary protocol on both ends, not a custom one.

Persistence: full-state snapshots to SQLite on every applied update. Simple
and correct; for very high-frequency edits at scale you'd batch snapshots
instead of writing on every keystroke, but correctness comes first here.
"""

import sqlite3
import datetime
from typing import Optional

from pycrdt import Doc, Text


def _docs_conn(db_path: str = "nexus_docs_crdt.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS crdt_documents (
            doc_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            snapshot BLOB,
            version INTEGER NOT NULL DEFAULT 0,
            owner TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


class CollaborativeDoc:
    """Wraps one pycrdt.Doc — the server's authoritative copy of one
    document. One instance per open document, held in memory while at
    least one client is connected; reloaded from its SQLite snapshot on
    first connect after a restart."""

    def __init__(self, doc_id: str, conn: Optional[sqlite3.Connection] = None):
        self.doc_id = doc_id
        self.conn = conn or _docs_conn()
        self.ydoc = Doc()
        self.ytext = self.ydoc.get("content", type=Text)
        self._load_snapshot()

    def _load_snapshot(self):
        row = self.conn.execute("SELECT snapshot FROM crdt_documents WHERE doc_id = ?", (self.doc_id,)).fetchone()
        if row and row[0]:
            self.ydoc.apply_update(row[0])

    def apply_remote_update(self, update_bytes: bytes):
        """Apply an update that arrived from a client. This is the core
        CRDT operation — merging is automatic and conflict-free regardless
        of what else has happened to this doc since the client's last sync."""
        self.ydoc.apply_update(update_bytes)

    def get_full_state(self) -> bytes:
        """The complete current document state as a single update — what a
        newly-connecting client applies to initialize itself."""
        return self.ydoc.get_update()

    def get_text(self) -> str:
        return str(self.ytext)

    def insert_local(self, index: int, text: str) -> bytes:
        """Server-side edit (e.g. from a non-CRDT-aware caller like a REST
        endpoint) — returns the update bytes produced, so callers can
        broadcast them the same way a client update would be broadcast."""
        with self.ydoc.transaction():
            self.ytext.insert(index, text)
        return self.get_full_state()

    def save_snapshot(self, title: str, owner: str):
        snapshot = self.get_full_state()
        ts = datetime.datetime.now(datetime.UTC).isoformat()
        self.conn.execute(
            "INSERT INTO crdt_documents (doc_id, title, snapshot, version, owner, updated_at) VALUES (?,?,?,1,?,?) "
            "ON CONFLICT(doc_id) DO UPDATE SET snapshot = excluded.snapshot, version = version + 1, updated_at = excluded.updated_at",
            (self.doc_id, title, snapshot, owner, ts),
        )
        self.conn.commit()


def list_documents(conn: Optional[sqlite3.Connection] = None) -> list:
    conn = conn or _docs_conn()
    rows = conn.execute("SELECT doc_id, title, version, owner, updated_at FROM crdt_documents ORDER BY updated_at DESC").fetchall()
    return [{"doc_id": r[0], "title": r[1], "version": r[2], "owner": r[3], "updated_at": r[4]} for r in rows]


class DocsRealtime:
    """Same cross-process broadcast pattern as chat_backend.RealtimeChat,
    carrying base64-encoded CRDT update bytes instead of chat JSON. Kept as
    a separate small class rather than generalizing RealtimeChat, because
    the payload semantics genuinely differ (binary CRDT ops vs. chat
    events) even though the transport pattern looks the same."""

    def __init__(self, redis_client):
        self.redis = redis_client

    def _channel(self, doc_id: str) -> str:
        return f"docs:room:{doc_id}"

    async def publish_update(self, doc_id: str, update_b64: str):
        await self.redis.publish(self._channel(doc_id), update_b64)

    async def subscribe(self, doc_id: str):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._channel(doc_id))
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = message["data"]
                yield data.decode() if isinstance(data, bytes) else data
        finally:
            try:
                await pubsub.unsubscribe(self._channel(doc_id))
                await pubsub.close()
            except Exception:
                pass  # best-effort cleanup during disconnect/cancellation — see meet_backend.py's subscribe_peer for the full rationale

