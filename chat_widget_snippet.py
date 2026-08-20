"""
Integration example: drop into 11___Collaboration_Portfolio.py as a new
"Team Chat" tab. Two pieces:
  1. Streamlit fetches a short-lived chat token server-to-server (the
     PLATFORM_API_KEY never reaches the browser).
  2. An embedded HTML/JS widget opens a real WebSocket directly from the
     browser to the FastAPI backend and renders messages as they arrive.

Honesty note: the WebSocket backend (chat_backend.py, the /ws/chat/{room_id}
endpoint in api_server.py) is verified end-to-end via the test suite shown
in this session — real auth rejection, real cross-connection delivery, real
typing indicators, all through FastAPI's actual WebSocket test client. What
is NOT verified here is this specific browser-side JavaScript actually
running in a real browser — this sandbox has no browser to run it in. The
JS is syntactically checked and follows the same message protocol the
backend test already proved correct; treat the first real browser test as
the actual verification of this piece specifically.
"""

import streamlit as st
import requests
import os

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
WS_BASE_URL = os.environ.get("WS_BASE_URL", "ws://localhost:8000")


def get_chat_token(user_email: str) -> str | None:
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/v1/chat/token",
            params={"email": user_email},
            headers={"X-API-Key": os.environ.get("PLATFORM_API_KEY", "")},
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()["token"]
    except Exception as e:
        st.error(f"Chat backend unavailable: {e}")
        return None


def render_team_chat(user_email: str, room_id: str = "general"):
    st.markdown("### 💬 Team Chat")

    token = get_chat_token(user_email)
    if not token:
        st.warning("Chat is currently unavailable — the FastAPI backend (api_server.py) needs to be running and reachable at API_BASE_URL.")
        return

    ws_url = f"{WS_BASE_URL}/ws/chat/{room_id}?token={token}"

    widget_html = f"""
    <div id="chat-container" style="border:1px solid #333;border-radius:8px;padding:10px;height:420px;display:flex;flex-direction:column;background:#0b1321;">
      <div id="chat-messages" style="flex:1;overflow-y:auto;margin-bottom:8px;"></div>
      <div id="chat-typing" style="font-size:0.8em;color:#94a3b8;height:18px;"></div>
      <div style="display:flex;gap:6px;">
        <input id="chat-input" type="text" placeholder="Type a message..."
               style="flex:1;padding:8px;border-radius:6px;border:1px solid #444;background:#111;color:#fff;" />
        <button id="chat-send" style="padding:8px 16px;border-radius:6px;background:#00f2fe;border:none;color:#000;font-weight:bold;">Send</button>
      </div>
    </div>
    <script>
    (function() {{
        const messagesEl = document.getElementById('chat-messages');
        const typingEl = document.getElementById('chat-typing');
        const inputEl = document.getElementById('chat-input');
        const sendBtn = document.getElementById('chat-send');
        const selfEmail = {user_email!r};

        const ws = new WebSocket({ws_url!r});
        let typingTimeout = null;

        function appendMessage(sender, content, sentAt) {{
            const isSelf = sender === selfEmail;
            const bubble = document.createElement('div');
            bubble.style.cssText = `margin:4px 0;display:flex;justify-content:${{isSelf ? 'flex-end' : 'flex-start'}};`;
            bubble.innerHTML = `
                <div style="max-width:70%;padding:8px 12px;border-radius:12px;
                            background:${{isSelf ? '#00838f' : '#1e293b'}};color:#fff;">
                    ${{isSelf ? '' : `<div style="font-size:0.75em;color:#94a3b8;">${{sender}}</div>`}}
                    <div>${{content}}</div>
                    <div style="font-size:0.65em;color:#cbd5e1;text-align:right;">${{new Date(sentAt).toLocaleTimeString()}}</div>
                </div>`;
            messagesEl.appendChild(bubble);
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }}

        ws.onmessage = (event) => {{
            const data = JSON.parse(event.data);
            if (data.type === 'history') {{
                data.messages.forEach(m => appendMessage(m.sender, m.content, m.sent_at));
            }} else if (data.type === 'message') {{
                appendMessage(data.sender, data.content, data.sent_at);
            }} else if (data.type === 'typing') {{
                if (data.user !== selfEmail) {{
                    typingEl.textContent = data.is_typing ? `${{data.user}} is typing...` : '';
                }}
            }}
        }};

        ws.onclose = (event) => {{
            typingEl.textContent = event.code === 4401
                ? 'Chat session expired — refresh the page.'
                : 'Disconnected from chat.';
        }};

        function sendMessage() {{
            const content = inputEl.value.trim();
            if (!content) return;
            ws.send(JSON.stringify({{type: 'message', content: content}}));
            inputEl.value = '';
        }}

        sendBtn.onclick = sendMessage;
        inputEl.addEventListener('keydown', (e) => {{
            if (e.key === 'Enter') sendMessage();
            else {{
                ws.send(JSON.stringify({{type: 'typing', is_typing: true}}));
                clearTimeout(typingTimeout);
                typingTimeout = setTimeout(() => ws.send(JSON.stringify({{type: 'typing', is_typing: false}})), 2000);
            }}
        }});

        // Heartbeat every 20s so presence doesn't expire (PRESENCE_TTL_SECONDS=45 server-side)
        setInterval(() => {{
            if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({{type: 'heartbeat'}}));
        }}, 20000);
    }})();
    </script>
    """

    st.components.v1.html(widget_html, height=460)