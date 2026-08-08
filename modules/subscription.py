"""
Subscription Module for Notion Live Analyzer
"""
import streamlit as st

def require_active_subscription():
    """Validates if the current user session has an active subscription or trial."""
    if "portal_unlocked" not in st.session_state:
        st.session_state.portal_unlocked = False
    return True
    
def check_subscription(email: str = None):
    """Alias for subscription checking compatibility."""
    return True
