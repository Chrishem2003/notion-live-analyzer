"""
🛡️ Admin Guard Module — Enforces super-administrator access control boundaries.
"""
import streamlit as st

def require_admin():
    """
    Validates if the currently authenticated user possesses administrative privileges.
    If unauthorized, halts execution and renders a security restriction warning.
    """
    user = st.session_state.get("user_identity")
    
    # Fallback check for session role state
    role = st.session_state.get("user_role", "user")
    
    # Check authorization status
    is_admin = False
    if role in ["admin", "superadmin"]:
        is_admin = True
    elif user and isinstance(user, dict):
        if user.get("role") in ["admin", "superadmin"]:
            is_admin = True

    if not is_admin:
        st.error("🚨 **Access Denied**: Administrative privileges are required to view the Sovereign Enterprise Control Plane.")
        st.warning("Please sign in using an authorized administrator account to access system diagnostics, RBAC, and security vaults.")
        st.stop()
