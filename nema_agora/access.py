"""Access guard helpers for Streamlit pages that rely on the main portal login."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def has_authenticated_portal_session(state: Mapping[str, Any]) -> bool:
    """Require the server-side identity populated by the main portal auth flow.

    This is a page access gate, not a replacement for authenticating the user.
    The main app must remain the only code path that establishes these session
    fields after validating credentials or completing a trusted OAuth callback.
    """
    if not isinstance(state, Mapping):
        return False
    if state.get("portal_unlocked") is not True:
        return False
    identity = state.get("user_identity")
    if not isinstance(identity, Mapping):
        return False
    email = identity.get("email")
    return isinstance(email, str) and bool(email.strip())
