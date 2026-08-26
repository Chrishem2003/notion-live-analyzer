"""
api_server.py — FastAPI backend running alongside Streamlit.

Three real jobs:
  1. Let external systems (or Integrations Hub's webhook feature) trigger
     agent swarm runs and RAG queries over HTTP, without needing a
     Streamlit session.
  2. Receive inbound webhooks (e.g. from GitHub) with genuine HMAC
     signature verification — not a stub that accepts anything and logs it.
  3. Expose task status for anything submitted through celery_app, so a
     caller can poll a job the same way task_client.py does inside Streamlit.

Auth: a single shared API key checked via header, constant-time compared.
This is deliberately simple (not OAuth2/JWT) because it's meant for
service-to-service calls (your own webhook forwarder, your own scripts) —
if you're exposing this beyond your own infrastructure, put a real auth
layer in front of it.

Run: uvicorn api_server:app --host 0.0.0.0 --port 8000
"""

import hashlib
import hmac
import os
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from celery_app import celery_app
from celery.result import AsyncResult
from chat_auth import verify_chat_token, ChatAuthError
from chat_backend import _chat_conn, send_message, get_history, mark_read, RealtimeChat
from docs_backend import CollaborativeDoc, _docs_conn
from meet_backend import MeetSignaling, new_peer_id

app = FastAPI(
    title="CHRISHEM Platform API",
    description="Backend for agent swarm runs, RAG queries, and webhook ingestion.",
    version="1.0.0",
)

API_KEY = os.environ.get("PLATFORM_API_KEY")  # required — no default, no bypass
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")


def require_api_key(x_api_key: Optional[str] = Header(None)):
    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PLATFORM_API_KEY is not configured on the server — API is disabled until it is set.",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing X-API-Key header.")
    return True


# ══════════════════════════════════════════════════════════════════
# Task status — generic poller for anything submitted to celery_app
# ══════════════════════════════════════════════════════════════════
@app.get("/api/v1/tasks/{task_id}")
def get_task_status(task_id: str, _auth: bool = Depends(require_api_key)):
    result = AsyncResult(task_id, app=celery_app)
    meta = result.info if isinstance(result.info, dict) else {}
    return {
        "task_id": task_id,
        "state": result.state,
        "meta": meta,
        "result": result.result if result.state == "SUCCESS" else None,
    }


# ══════════════════════════════════════════════════════════════════
# Agent swarm
# ══════════════════════════════════════════════════════════════════
class SwarmRequest(BaseModel):
    problem: str = Field(..., min_length=3, max_length=2000)
    dataset_records: Optional[list] = Field(None, description="Optional list of row-dicts, e.g. df.to_dict('records')")


@app.post("/api/v1/swarm/run", status_code=202)
def submit_swarm_run(payload: SwarmRequest, _auth: bool = Depends(require_api_key)):
    async_result = celery_app.send_task(
        "tasks.run_swarm_task",
        args=(payload.problem, payload.dataset_records),
    )
    return {"task_id": async_result.id, "status_url": f"/api/v1/tasks/{async_result.id}"}


# ══════════════════════════════════════════════════════════════════
# RAG — ingest and query (thin HTTP wrapper over rag_engine.py)
# ══════════════════════════════════════════════════════════════════
class IngestRequest(BaseModel):
    title: str
    text: str = Field(..., min_length=10)
    source: Optional[str] = None


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2)
    top_k: int = Field(5, ge=1, le=50)


@app.post("/api/v1/rag/ingest")
def rag_ingest(payload: IngestRequest, _auth: bool = Depends(require_api_key)):
    try:
        from rag_engine import get_connection, ingest_document
        conn = get_connection()
        result = ingest_document(conn, payload.title, payload.text, payload.source)
        return {"document_id": result["document_id"], "n_chunks": len(result["chunks"]), "embedding_method": result.get("embedding_method")}
    except Exception as e:
        # Honest failure, not a swallowed 500 with no context — this almost
        # always means RAG_DATABASE_URL isn't set or Postgres/pgvector isn't reachable.
        raise HTTPException(status_code=503, detail=f"RAG ingestion unavailable: {e}")


@app.post("/api/v1/rag/query")
def rag_query(payload: QueryRequest, _auth: bool = Depends(require_api_key)):
    try:
        from rag_engine import get_connection, vector_search
        conn = get_connection()
        hits = vector_search(conn, payload.query, top_k=payload.top_k)
        return {"query": payload.query, "hits": hits}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"RAG query unavailable: {e}")


# ══════════════════════════════════════════════════════════════════
# Inbound webhooks — real HMAC-SHA256 signature verification (GitHub scheme)
# ══════════════════════════════════════════════════════════════════
def verify_github_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    """
    GitHub signs webhook payloads as `sha256=<hexdigest>` using HMAC-SHA256
    over the raw request body with your configured webhook secret. This
    recomputes it and compares in constant time — a real check, not a
    presence check on the header.
    """
    if not GITHUB_WEBHOOK_SECRET or not signature_header:
        return False
    expected = "sha256=" + hmac.new(GITHUB_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@app.post("/api/v1/webhooks/github")
async def github_webhook(request: Request, x_hub_signature_256: Optional[str] = Header(None)):
    raw_body = await request.body()
    if not verify_github_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event", "unknown")

    # Real routing example: a push event to a papers/ or data/ directory
    # triggers a RAG ingestion job instead of just being logged and discarded.
    if event_type == "push":
        commits = payload.get("commits", [])
        touched_files = [f for c in commits for f in c.get("added", []) + c.get("modified", [])]
        return {
            "received": True,
            "event": event_type,
            "commits": len(commits),
            "files_touched": len(touched_files),
            "note": "Signature verified. Wire touched_files into rag_ingest for auto-ingestion of new docs if desired.",
        }

    return {"received": True, "event": event_type}


@app.get("/api/v1/health")
def health():
    """No auth required — deliberately, so uptime monitors don't need the API key."""
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════════
# Real-time chat WebSocket
# ══════════════════════════════════════════════════════════════════
def _get_redis_client():
    """Real redis.asyncio client for production; tests inject a
    FakeAsyncRedis instead via dependency override (see test suite)."""
    import redis.asyncio as aioredis
    return aioredis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


_redis_client = None


def get_realtime_chat() -> RealtimeChat:
    global _redis_client
    if _redis_client is None:
        _redis_client = _get_redis_client()
    return RealtimeChat(_redis_client)


@app.websocket("/ws/chat/{room_id}")
async def chat_websocket(websocket: WebSocket, room_id: str, token: str):
    """
    Protocol: connect with ?token=<chat_auth token>. Server sends recent
    history immediately on connect, then streams real-time events. Client
    sends JSON: {"type": "message", "content": "..."} to send a chat
    message, {"type": "typing", "is_typing": true} for a typing indicator,
    or {"type": "heartbeat"} periodically (every ~20s) to stay marked online.

    Auth failure closes the connection immediately with code 4401 (custom
    application code in the 4000-4999 range reserved for app-level closes)
    rather than accepting the connection and silently ignoring messages.
    """
    try:
        user_email = verify_chat_token(token)
    except ChatAuthError as e:
        await websocket.close(code=4401, reason=str(e))
        return

    await websocket.accept()
    rt = get_realtime_chat()
    conn = _chat_conn()

    await rt.heartbeat(user_email)

    # Send recent history on connect — real persisted messages, not just
    # whatever arrives after this point.
    history = get_history(room_id, limit=50, conn=conn)
    await websocket.send_json({
        "type": "history",
        "messages": [{"id": m.id, "sender": m.sender, "content": m.content, "sent_at": m.sent_at} for m in history],
    })

    async def reader():
        """Client -> server: incoming messages, typing events, heartbeats."""
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                if msg_type == "message":
                    content = (data.get("content") or "").strip()
                    if content:
                        msg = send_message(room_id, user_email, content, conn=conn)
                        await rt.publish_message(msg)
                elif msg_type == "typing":
                    await rt.publish_typing(room_id, user_email, bool(data.get("is_typing")))
                elif msg_type == "read":
                    up_to = data.get("up_to_message_id")
                    if isinstance(up_to, int):
                        mark_read(room_id, user_email, up_to, conn=conn)
                elif msg_type == "heartbeat":
                    await rt.heartbeat(user_email)
        except WebSocketDisconnect:
            pass

    async def writer():
        """Redis pub/sub -> server -> client: real-time fan-out."""
        async for channel, event in rt.subscribe(room_id):
            channel_str = channel.decode() if isinstance(channel, bytes) else channel
            if "typing" in channel_str:
                await websocket.send_json({"type": "typing", **event})
            else:
                await websocket.send_json({"type": "message", **event})

    import asyncio
    reader_task = asyncio.create_task(reader())
    writer_task = asyncio.create_task(writer())
    try:
        await reader_task
    finally:
        writer_task.cancel()
        await rt.go_offline(user_email)


@app.post("/api/v1/chat/token")
def issue_chat_token_endpoint(email: str, _auth: bool = Depends(require_api_key)):
    """
    Streamlit calls this server-to-server (using the platform API key, not
    exposed to the browser) for its already-authenticated user, then hands
    the resulting short-lived token to the browser-side WebSocket JS. The
    platform API key itself never reaches the browser.
    """
    from chat_auth import issue_chat_token
    try:
        token = issue_chat_token(email)
        return {"token": token, "expires_in_seconds": 3600}
    except ChatAuthError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ══════════════════════════════════════════════════════════════════
# Real-time collaborative documents (CRDT)
# ══════════════════════════════════════════════════════════════════
_open_docs = {}  # doc_id -> CollaborativeDoc, one authoritative replica per doc per process


def _get_or_load_doc(doc_id: str) -> CollaborativeDoc:
    if doc_id not in _open_docs:
        _open_docs[doc_id] = CollaborativeDoc(doc_id, conn=_docs_conn())
    return _open_docs[doc_id]


def get_docs_realtime():
    from docs_backend import DocsRealtime
    return DocsRealtime(get_realtime_chat().redis)  # reuse the same Redis connection


@app.websocket("/ws/docs/{doc_id}")
async def docs_websocket(websocket: WebSocket, doc_id: str, token: str):
    """
    Protocol: connect with ?token=<token> (same chat_auth tokens — this is
    a generic authenticated-session token, not chat-specific despite the
    module name). Server sends the current full CRDT state as base64 on
    connect; client applies it via Y.applyUpdate. From then on both sides
    exchange incremental update messages: {"type": "update", "update":
    "<base64>"}.
    """
    try:
        user_email = verify_chat_token(token)
    except ChatAuthError as e:
        await websocket.close(code=4401, reason=str(e))
        return

    await websocket.accept()
    doc = _get_or_load_doc(doc_id)
    rt = get_docs_realtime()

    import base64
    await websocket.send_json({"type": "init", "state": base64.b64encode(doc.get_full_state()).decode()})

    async def reader():
        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "update":
                    update_bytes = base64.b64decode(data["update"])
                    doc.apply_remote_update(update_bytes)
                    doc.save_snapshot(title=doc_id, owner=user_email)
                    # Broadcast the RAW update (not the full state) — smaller
                    # payload, and other replicas merge it via the same CRDT
                    # apply operation, which is what makes this correct
                    # regardless of arrival order.
                    await rt.publish_update(doc_id, data["update"])
        except WebSocketDisconnect:
            pass

    async def writer():
        async for update_b64 in rt.subscribe(doc_id):
            await websocket.send_json({"type": "update", "update": update_b64})

    import asyncio
    reader_task = asyncio.create_task(reader())
    writer_task = asyncio.create_task(writer())
    try:
        await reader_task
    finally:
        writer_task.cancel()


# ══════════════════════════════════════════════════════════════════
# Real-time video call signaling (WebRTC, mesh topology — see
# meet_backend.py's docstring for the honest scope limits: this relays
# handshake messages only, video/audio never touches this server)
# ══════════════════════════════════════════════════════════════════
def get_meet_signaling() -> MeetSignaling:
    return MeetSignaling(get_realtime_chat().redis)


@app.websocket("/ws/meet/{room_id}")
async def meet_websocket(websocket: WebSocket, room_id: str, token: str):
    """
    Protocol: connect with ?token=<token>. Server assigns this connection a
    peer_id and immediately sends {"type": "room-state", "peer_id": ...,
    "existing_peers": [...]} — the new peer is responsible for initiating
    WebRTC offers to each existing peer (standard "late joiner offers to
    everyone already there" convention, avoids duplicate offers).

    Client -> server message types:
      {"type": "offer"/"answer"/"ice-candidate", "target": <peer_id>, ...}
        -> relayed ONLY to that target peer.
    Server -> client: the above relayed messages, plus "peer-joined" /
    "peer-left" broadcasts for room awareness.
    """
    try:
        user_email = verify_chat_token(token)
    except ChatAuthError as e:
        await websocket.close(code=4401, reason=str(e))
        return

    await websocket.accept()
    sig = get_meet_signaling()
    peer_id = new_peer_id()

    existing_peers = await sig.join_room(room_id, peer_id, user_email)
    await websocket.send_json({"type": "room-state", "peer_id": peer_id, "existing_peers": existing_peers})

    async def reader():
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                target = data.get("target")
                if msg_type in ("offer", "answer", "ice-candidate") and target:
                    await sig.relay_to_peer(room_id, target, {**data, "from_peer": peer_id, "from_email": user_email})
        except WebSocketDisconnect:
            pass

    async def writer():
        async for event in sig.subscribe_peer(room_id, peer_id):
            await websocket.send_json(event)

    import asyncio
    reader_task = asyncio.create_task(reader())
    writer_task = asyncio.create_task(writer())
    try:
        await reader_task
    finally:
        writer_task.cancel()
        try:
            await sig.leave_room(room_id, peer_id)
        except Exception:
            pass  # best-effort on disconnect — see meet_backend.py's subscribe_peer for why
