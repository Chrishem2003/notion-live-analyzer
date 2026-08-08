"""
modules/admin_guard.py
Server-side admin gate and sovereign security control center.
Provides robust role-based access control (RBAC), session identity verification,
and administrative enforcement across all platform modules.
"""

import streamlit as st

def is_admin() -> bool:
    """Returns True if the current user session has administrator or sovereign privileges."""
    identity = st.session_state.get("user_identity", {})
    role = str(identity.get("role", "")).lower()
    
    # Check session identity role, explicit session flags, or fallback admin names
    is_admin_role = role in ["admin", "sovereign administrator", "administrator"]
    session_flag = st.session_state.get("is_admin", False)
    username = str(identity.get("name", "")).lower()
    is_root_user = username in ["chrishem", "chris shem", "kula chris"]

    return bool(is_admin_role or session_flag or is_root_user)


def require_admin():
    """Enforces administrative gatekeeping. Halts execution and displays an error if unauthorized."""
    if not is_admin():
        st.error("🚫 Access Denied: Sovereign Administrator privileges are required to view this module.")
        st.stop()


def render_admin_security_badge():
    """Renders a secure administrative status indicator in the sidebar or active panel."""
    if is_admin():
        st.sidebar.markdown('<span style="color: #34D399; font-size: 0.8rem; font-weight: 700;">🛡️ Sovereign Admin Active</span>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown('<span style="color: #94A3B8; font-size: 0.8rem;">🔒 Standard User Enclave</span>', unsafe_allow_html=True)