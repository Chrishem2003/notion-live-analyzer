"""
modules/admin_guard.py
Server-side admin gate. Import and call require_admin() at the top of
10_Admin_Security_Center.py's main(), and use is_admin() to hide the
hub link in navigation for everyone else.

This replaces the old pattern of trusting a role the user picked from a
sidebar dropdown, or an email typed into a login box.
"""

import streamlit as st


def is_admin() -> bool:
    identity = st.session_state.get("user_identity", {})
    return identity.get("role") == "admin"


def require_admin():
    if not is_admin():
        st.error("🚫 You don't have permission to view this page.")
        st.stop()
