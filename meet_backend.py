"""
meet_backend.py — WebRTC signaling server.

Important scope note, stated once here rather than buried: this is a
SIGNALING server, not a media server. It never touches audio/video bytes —
it only relays the SDP offers/answers and ICE candidates peers need to
establish a DIRECT peer-to-peer connection with each other. Once that
handshake completes, video/audio flows browser-to-browser (mesh topology),
not through this server at all.

That means: works well for 2-4 participants (each peer uploads its video
stream N-1 times, once per other participant — fine for a small call, bad
for 10+ people). A real "Google Meet at scale" needs an SFU (Selective
Forwarding Unit) that receives each stream once and re-distributes it
server-side — that's substantially more infrastructure (media servers like
mediasoup, Janus, or LiveKit) and is out of scope for this pass.

Room membership and message routing are backed by Redis (not local
process memory) for the same reason as chat/docs: a real deployment runs
multiple worker processes, and peer A's browser might be connected to a
different worker than peer B's.
"""

import json
import uuid
from typing import Optional


class MeetSignaling:
    def __init__(self, redis_client):
        self.redis = redis_client

    def _members_key(self, room_id: str) -> str:
        return f"meet:members:{room_id}"

    def _room_channel(self, room_id: str) -> str:
        return f"meet:room:{room_id}"

    def _peer_channel(self, room_id: str, peer_id: str) -> str:
        return f"meet:peer:{room_id}:{peer_id}"

    async def join_room(self, room_id: str, peer_id: str, user_email: str) -> list:
        """Registers this peer as a room member and returns the list of
        OTHER members already present (so the new peer knows who to
        initiate WebRTC offers to)."""
        existing_raw = await self.redis.hgetall(self._members_key(room_id))
        existing = [
            {"peer_id": pid.decode() if isinstance(pid, bytes) else pid,
             "user_email": email.decode() if isinstance(email, bytes) else email}
            for pid, email in existing_raw.items()
        ]
        await self.redis.hset(self._members_key(room_id), peer_id, user_email)
        await self.broadcast_to_room(room_id, {"type": "peer-joined", "peer_id": peer_id, "user_email": user_email}, exclude_peer_id=peer_id)
        return existing

    async def leave_room(self, room_id: str, peer_id: str):
        await self.redis.hdel(self._members_key(room_id), peer_id)
        await self.broadcast_to_room(room_id, {"type": "peer-left", "peer_id": peer_id})

    async def relay_to_peer(self, room_id: str, target_peer_id: str, message: dict):
        """Targeted delivery — only the named peer's subscriber receives
        this. Used for offer/answer/ICE candidates, which must go to
        exactly one recipient, not the whole room."""
        await self.redis.publish(self._peer_channel(room_id, target_peer_id), json.dumps(message))

    async def broadcast_to_room(self, room_id: str, message: dict, exclude_peer_id: Optional[str] = None):
        payload = dict(message)
        if exclude_peer_id:
            payload["_exclude"] = exclude_peer_id
        await self.redis.publish(self._room_channel(room_id), json.dumps(payload))

    async def subscribe_peer(self, room_id: str, peer_id: str):
        """Yields every message meant for this peer: targeted signaling
        messages on its private channel, plus room-wide join/leave
        broadcasts (skipping ones the sender excluded, e.g. so a peer
        doesn't get notified of its own join)."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._peer_channel(room_id, peer_id), self._room_channel(room_id))
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                data = json.loads(message["data"])
                if data.get("_exclude") == peer_id:
                    continue
                data.pop("_exclude", None)
                yield data
        finally:
            try:
                await pubsub.unsubscribe(self._peer_channel(room_id, peer_id), self._room_channel(room_id))
                await pubsub.close()
            except Exception:
                # Cleanup best-effort during disconnect/cancellation — a
                # failure here (e.g. the event loop tearing down mid-close,
                # observed under some test-client threading models) must
                # not mask the real error that triggered cleanup, nor crash
                # the handler on the way out.
                pass


def new_peer_id() -> str:
    return uuid.uuid4().hex[:12]
