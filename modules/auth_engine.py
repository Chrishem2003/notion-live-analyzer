import security_guard
import security_guard

import streamlit as st

def initialize_rbac():
    """Initializes user session state roles."""
    if "user_role" not in st.session_state:
        st.session_state["user_role"] = "Analyst"

def check_permission(required_role: str) -> bool:
    """Checks if the active user role meets permission requirements."""
    role_hierarchy = {"Viewer": 1, "Analyst": 2, "Admin": 3}
    current = role_hierarchy.get(st.session_state.get("user_role", "Viewer"), 1)
    required = role_hierarchy.get(required_role, 3)
    return current >= required
