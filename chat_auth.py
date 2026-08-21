"""
chat_auth.py â€” Signed, time-limited tokens bridging Streamlit's session
auth to the FastAPI WebSocket process.

Why this exists: Streamlit and the FastAPI backend are separate processes
(see api_server.py's docstring) â€” they don't share session state. A user
who's already logged into Streamlit needs some way to prove that to the
WebSocket endpoint without logging in twice. This is a real HMAC-SHA256
signed token with an expiry, verified server-side â€” not a shared secret
handed to the browser, and not a bypassable client-supplied claim.

Set CHAT_TOKEN_SECRET to a real random value in production (openssl rand
-hex 32). If unset, this refuses to issue or verify tokens rather than
falling back to a guessable default â€” a hardcoded default secret here
would be exactly the kind of security hole this platform's audit has been
removing elsewhere.
"""

import hmac
import hashlib
import os
import time
import base64
import json


class ChatAuthError(Exception):
    pass


def _secret() -> bytes:
    secret = os.environ.get("CHAT_TOKEN_SECRET")
    if not secret:
        raise ChatAuthError("CHAT_TOKEN_SECRET is not set â€” chat auth is disabled until it is configured.")
    return secret.encode()


def issue_chat_token(email: str, ttl_seconds: int = 3600) -> str:
    """Real HMAC signature over (email, expiry) â€” a client can read the
    payload but cannot forge a valid signature without the server secret."""
    payload = {"email": email.strip().lower(), "exp": int(time.time()) + ttl_seconds}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode()
    signature = hmac.new(_secret(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_chat_token(token: str) -> str:
    """Returns the verified email, or raises ChatAuthError. Constant-time
    signature comparison; explicit expiry check; no silent fallback."""
    try:
        payload_b64, signature = token.rsplit(".", 1)
    except ValueError:
        raise ChatAuthError("Malformed token.")

    expected_sig = hmac.new(_secret(), payload_b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, signature):
        raise ChatAuthError("Invalid token signature.")

    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()))
    except Exception:
        raise ChatAuthError("Malformed token payload.")

    if payload.get("exp", 0) < time.time():
        raise ChatAuthError("Token expired.")

    email = payload.get("email")
    if not email:
        raise ChatAuthError("Token missing email claim.")
    return email
