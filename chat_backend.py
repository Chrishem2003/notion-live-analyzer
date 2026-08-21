"""
chat_backend.py â€” Real-time messaging backend.

Two storage layers, each doing the job it's actually suited for:
  - SQLite: durable message history, read receipts. Source of truth.
  - Redis pub/sub: real-time fan-out ONLY. A message is written to SQLite
    first, then published â€” if Redis is briefly down, you lose real-time
    delivery to currently-connected clients, not the message itself (they
    get it on next history fetch/reconnect).

Why Redis pub/sub at all, and not just an in-memory dict of connections:
a production FastAPI deployment typically runs multiple worker processes
(or multiple replicas). If Alice is connected to worker A and Bob to
worker B, an in-memory broadcast on worker A never reaches Bob. Redis
pub/sub is what makes the broadcast actually cross-process. This is a real
bug class in naive chat tutorials â€” the in-memory version works perfectly
in every local demo and silently drops messages in production.

Presence: a Redis key per user with a TTL, renewed by a heartbeat the
client sends periodically over the same WebSocket. No heartbeat within the
TTL window = offline. This is real "last seen" tracking, not a static flag.
"""

import json
import time
import sqlite3
import datetime
from dataclasses import dataclass, asdict
from typing import Optional, AsyncIterator

PRESENCE_TTL_SECONDS = 45  # client should heartbeat well under this, e.g. every 20s


def _chat_conn(db_path: str = "nexus_chat.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            sent_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_read_receipts (
            room_id TEXT NOT NULL,
            user_email TEXT NOT NULL,
            last_read_message_id INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (room_id, user_email)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_room ON chat_messages(room_id, id)")
    conn.commit()
    return conn


@dataclass
class ChatMessage:
    id: int
    room_id: str
    sender: str
    content: str
    sent_at: str


def send_message(room_id: str, sender: str, content: str, conn: Optional[sqlite3.Connection] = None) -> ChatMessage:
    """Persist first (source of truth), return the row with its real id â€”
    callers publish this to Redis themselves so the async publish can be
    awaited properly (this function stays sync/DB-only)."""
    conn = conn or _chat_conn()
    ts = datetime.datetime.utcnow().isoformat()
    cur = conn.execute(
        "INSERT INTO chat_messages (room_id, sender, content, sent_at) VALUES (?,?,?,?)",
        (room_id, sender, content, ts),
    )
    conn.commit()
    return ChatMessage(id=cur.lastrowid, room_id=room_id, sender=sender, content=content, sent_at=ts)


def get_history(room_id: str, since_id: int = 0, limit: int = 100, conn: Optional[sqlite3.Connection] = None) -> list:
    conn = conn or _chat_conn()
    rows = conn.execute(
        "SELECT id, room_id, sender, content, sent_at FROM chat_messages WHERE room_id = ? AND id > ? ORDER BY id ASC LIMIT ?",
        (room_id, since_id, limit),
    ).fetchall()
    return [ChatMessage(*r) for r in rows]


def mark_read(room_id: str, user_email: str, up_to_message_id: int, conn: Optional[sqlite3.Connection] = None):
    conn = conn or _chat_conn()
    ts = datetime.datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO chat_read_receipts (room_id, user_email, last_read_message_id, updated_at) VALUES (?,?,?,?) "
        "ON CONFLICT(room_id, user_email) DO UPDATE SET last_read_message_id = MAX(last_read_message_id, excluded.last_read_message_id), updated_at = excluded.updated_at",
        (room_id, user_email, up_to_message_id, ts),
    )
    conn.commit()


def get_read_receipts(room_id: str, conn: Optional[sqlite3.Connection] = None) -> dict:
    """Returns {user_email: last_read_message_id} for a room â€” enough for
    the UI to render WhatsApp-style double-check marks per message."""
    conn = conn or _chat_conn()
    rows = conn.execute(
        "SELECT user_email, last_read_message_id FROM chat_read_receipts WHERE room_id = ?", (room_id,)
    ).fetchall()
    return {r[0]: r[1] for r in rows}


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Real-time layer (Redis pub/sub + presence) â€” async, used by the
# WebSocket endpoint in api_server.py
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class RealtimeChat:
    def __init__(self, redis_client):
        """`redis_client` is a redis.asyncio.Redis instance (or a
        FakeAsyncRedis in tests) â€” dependency-injected so tests don't need
        a live Redis server."""
        self.redis = redis_client

    def _channel(self, room_id: str) -> str:
        return f"chat:room:{room_id}}"

    def _typing_channel(self, room_id: str) -> str:
        return f"chat:typing:{room_id}}"

    def _presence_key(self, user_email: str) -> str:
        return f"chat:presence:{user_email}}"

    async def publish_message(self, msg: ChatMessage):
        await self.redis.publish(self._channel(msg.room_id), json.dumps(asdict(msg)))

    async def publish_typing(self, room_id: str, user_email: str, is_typing: bool):
        await self.redis.publish(self._typing_channel(room_id), json.dumps({"user": user_email, "is_typing": is_typing}))

    async def heartbeat(self, user_email: str):
        """Renews presence TTL â€” call this on every heartbeat message the
        client sends, and once on connect."""
        await self.redis.set(self._presence_key(user_email), "1", ex=PRESENCE_TTL_SECONDS)

    async def go_offline(self, user_email: str):
        """Call on clean disconnect so 'online' clears immediately instead
        of waiting out the TTL."""
        await self.redis.delete(self._presence_key(user_email))

    async def is_online(self, user_email: str) -> bool:
        return await self.redis.exists(self._presence_key(user_email)) > 0

    async def subscribe(self, room_id: str):
        """Async generator yielding real-time events for a room (chat
        messages + typing indicators) until the caller stops iterating.
        Used inside the WebSocket handler's read loop."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._channel(room_id), self._typing_channel(room_id))
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                yield message["channel"], json.loads(message["data"])
        finally:
            try:
                await pubsub.unsubscribe(self._channel(room_id), self._typing_channel(room_id))
                await pubsub.close()
            except Exception:
                pass  # best-effort cleanup during disconnect/cancellation â€” see meet_backend.py's subscribe_peer for the full rationale
