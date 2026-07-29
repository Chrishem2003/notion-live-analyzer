"""
Advanced System Middleware & Error Interceptor
Handles crash recovery, session sanitization, and global state tracking.
"""
import streamlit as st
import traceback

def initialize_system_state():
    """Ensures core session variables exist across all modules."""
    if "app_initialized" not in st.session_state:
        st.session_state.app_initialized = True
        st.session_state.active_filters = {}
        st.session_state.error_logs = []

def handle_page_errors(func):
    """Decorator to catch unexpected exceptions and render safe fallback UI."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error("⚠️ An unexpected runtime exception occurred.")
            with st.expander("🔬 View Diagnostic Traceback"):
                tb_str = traceback.format_exc()
                st.code(tb_str, language="python")
                st.session_state.error_logs.append(tb_str)
            if st.button("🔄 Reset Session State"):
                st.session_state.clear()
                st.rerun()
    return wrapper
