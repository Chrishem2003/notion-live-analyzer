"""
Admin Guard Module
Provides role verification functions to restrict administrative pages to authorized personnel.
"""

import streamlit as st
from modules import auth_store

def require_admin():
    """
    Checks if the currently authenticated user has super-admin or admin privileges.
    Halts execution and shows an error banner if unauthorized.
    """
    # Check if user identity exists in session state
    user_identity = st.session_state.get("user_identity")
    
    if not user_identity:
        st.error("🚨 Access Denied: Authentication required to access the Admin & Security Center.")
        st.stop()
        
    email = user_identity.get("email")
    role = auth_store.get_role(email) if email else "user"
    
    # Allow access if user is super_admin or admin
    if role not in ["super_admin", "admin"]:
        st.error(f"🚨 Security Violation: Insufficient privileges for `{email}` (Role: `{role}`). Administrative clearance required.")
        st.stop()