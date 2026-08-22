"""
Integration example: drop into 11___Collaboration_Portfolio.py or
10____Admin_Security_Center.py's Meet tab (replacing the fixed NexusMeet
UI's placeholder "video isn't configured yet" state once this is deployed
— set MEET_BASE_URL to wherever api_server.py is actually reachable).

Scope reminder (see meet_backend.py's docstring): mesh topology, good for
2-4 participants. Each browser connects directly to every other browser
once signaling completes; this server never sees video/audio.
"""

import streamlit as st
import requests
import os

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
WS_BASE_URL = os.environ.get("WS_BASE_URL", "ws://localhost:8000")


def get_chat_token(user_email: str) -> str | None:
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/v1/chat/token", params={"email": user_email},
            headers={"X-API-Key": os.environ.get("PLATFORM_API_KEY", "")}, timeout=5,
        )
        resp.raise_for_status()
        return resp.json()["token"]
    except Exception as e:
        st.error(f"Meet backend unavailable: {e}")
        return None


def render_video_call(user_email: str, room_id: str):
    st.markdown(f"### 🎥 Live Call: {room_id}")
    st.caption("Direct peer-to-peer video (mesh) — works well for small groups (2-4 people).")

    token = get_chat_token(user_email)
    if not token:
        return

    ws_url = f"{WS_BASE_URL}/ws/meet/{room_id}?token={token}"

    widget_html = f"""
    <div id="meet-status" style="font-size:0.85em;color:#6B7280;margin-bottom:8px;">Requesting camera/mic access...</div>
    <div id="video-grid" style="display:flex;gap:8px;flex-wrap:wrap;">
        <video id="local-video" autoplay playsinline muted
               style="width:220px;height:165px;background:#000;border-radius:8px;border:2px solid #e8a33d;"></video>
    </div>
    <div style="margin-top:8px;">
        <button id="mute-btn" style="padding:6px 14px;border-radius:6px;background:#3A4048;color:#fff;border:none;">🎤 Mute</button>
        <button id="video-btn" style="padding:6px 14px;border-radius:6px;background:#3A4048;color:#fff;border:none;">📷 Camera Off</button>
        <button id="leave-btn" style="padding:6px 14px;border-radius:6px;background:#b91c1c;color:#fff;border:none;">📞 Leave</button>
    </div>
    <script>
    (function() {{
        const statusEl = document.getElementById('meet-status');
        const grid = document.getElementById('video-grid');
        const localVideo = document.getElementById('local-video');
        const selfEmail = {user_email!r};

        const ICE_SERVERS = [{{urls: 'stun:stun.l.google.com:19302'}];  // real, free, public Google STUN server

        let localStream = null;
        let myPeerId = null;
        const peerConnections = {{};  // peer_id -> RTCPeerConnection
        const ws = new WebSocket({ws_url!r});

        function addRemoteVideo(peerId) {{
            if (document.getElementById('video-' + peerId)) return;
            const v = document.createElement('video');
            v.id = 'video-' + peerId;
            v.autoplay = true;
            v.playsinline = true;
            v.style.cssText = 'width:220px;height:165px;background:#000;border-radius:8px;border:2px solid #3A4048;';
            grid.appendChild(v);
        }
        function removeRemoteVideo(peerId) {{
            const v = document.getElementById('video-' + peerId);
            if (v) v.remove();
            if (peerConnections[peerId]) {{
                peerConnections[peerId].close();
                delete peerConnections[peerId];
            }
        }

        function createPeerConnection(targetPeerId) {{
            const pc = new RTCPeerConnection({{iceServers: ICE_SERVERS});
            localStream.getTracks().forEach(track => pc.addTrack(track, localStream));

            pc.onicecandidate = (event) => {{
                if (event.candidate) {{
                    ws.send(JSON.stringify({{type: 'ice-candidate', target: targetPeerId, candidate: event.candidate}));
                }
            };
            pc.ontrack = (event) => {{
                addRemoteVideo(targetPeerId);
                document.getElementById('video-' + targetPeerId).srcObject = event.streams[0];
            };
            peerConnections[targetPeerId] = pc;
            return pc;
        }

        navigator.mediaDevices.getUserMedia({{video: true, audio: true}).then(stream => {{
            localStream = stream;
            localVideo.srcObject = stream;
            statusEl.textContent = 'Camera ready — connecting to call...';
        }).catch(err => {{
            statusEl.textContent = 'Camera/mic access denied or unavailable: ' + err.message + ' (you can still join audio-only if you retry with mic-only permissions)';
        });

        ws.onmessage = async (event) => {{
            const data = JSON.parse(event.data);

            if (data.type === 'room-state') {{
                myPeerId = data.peer_id;
                statusEl.textContent = `Connected. ${{data.existing_peers.length} other participant(s) in room.`;
                // Late joiner initiates offers to everyone already present
                for (const peer of data.existing_peers) {{
                    if (!localStream) await new Promise(r => setTimeout(r, 500));  // wait briefly for camera if not ready yet
                    const pc = createPeerConnection(peer.peer_id);
                    const offer = await pc.createOffer();
                    await pc.setLocalDescription(offer);
                    ws.send(JSON.stringify({{type: 'offer', target: peer.peer_id, sdp: offer}));
                }
            } else if (data.type === 'peer-joined') {{
                statusEl.textContent = `${{data.user_email} joined.`;
            } else if (data.type === 'peer-left') {{
                removeRemoteVideo(data.from_peer || data.peer_id);
            } else if (data.type === 'offer') {{
                const pc = createPeerConnection(data.from_peer);
                await pc.setRemoteDescription(data.sdp);
                const answer = await pc.createAnswer();
                await pc.setLocalDescription(answer);
                ws.send(JSON.stringify({{type: 'answer', target: data.from_peer, sdp: answer}));
            } else if (data.type === 'answer') {{
                const pc = peerConnections[data.from_peer];
                if (pc) await pc.setRemoteDescription(data.sdp);
            } else if (data.type === 'ice-candidate') {{
                const pc = peerConnections[data.from_peer];
                if (pc) await pc.addIceCandidate(data.candidate);
            }
        };

        ws.onclose = (event) => {{
            statusEl.textContent = event.code === 4401 ? 'Session expired — refresh.' : 'Call ended.';
        };

        document.getElementById('mute-btn').onclick = () => {{
            if (!localStream) return;
            localStream.getAudioTracks().forEach(t => t.enabled = !t.enabled);
        };
        document.getElementById('video-btn').onclick = () => {{
            if (!localStream) return;
            localStream.getVideoTracks().forEach(t => t.enabled = !t.enabled);
        };
        document.getElementById('leave-btn').onclick = () => {{
            Object.keys(peerConnections).forEach(removeRemoteVideo);
            if (localStream) localStream.getTracks().forEach(t => t.stop());
            ws.close();
        };
    })();
    </script>
    """
    st.components.v1.html(widget_html, height=380)
    st.caption(
        "⚠️ Real limitations, stated plainly: (1) mesh topology — beyond ~4 participants, "
        "upload bandwidth per person becomes the bottleneck; (2) uses Google's public STUN "
        "server only — some strict corporate/mobile NATs need a TURN server (relay) to connect "
        "at all, which isn't configured here; (3) this specific browser code has not been "
        "run against a real browser in this environment — the signaling server it depends on has."
    )
