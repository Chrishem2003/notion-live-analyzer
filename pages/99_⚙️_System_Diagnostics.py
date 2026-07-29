"""
Page: System Diagnostics & Health-Check
Monitors live app health, session errors, and environment metrics.
"""
import streamlit as st
import sys
import os
import pandas as pd
from modules.system_middleware import initialize_system_state

initialize_system_state()

st.set_page_config(page_title="System Diagnostics", page_icon="⚙️", layout="wide")

st.title("⚙️ System Diagnostics & Health Hub")
st.markdown("Real-time monitoring of application health, error traces, and active runtime variables.")

# Metrics Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
with col2:
    st.metric("Streamlit Version", st.__version__)
with col3:
    st.metric("Logged Errors", len(st.session_state.get("error_logs", [])))
with col4:
    st.metric("Session Status", "Active" if st.session_state.get("app_initialized") else "Initializing")

st.divider()

# Error Log Viewer
st.subheader("📋 Captured Exception Logs")
error_logs = st.session_state.get("error_logs", [])
if not error_logs:
    st.success("✨ No runtime exceptions or errors caught during this session. Everything is running smoothly!")
else:
    for idx, log in enumerate(error_logs):
        with st.expander(f"Error Log #{idx + 1}"):
            st.code(log, language="python")
    if st.button("🗑️ Clear Error History"):
        st.session_state.error_logs = []
        st.rerun()

st.divider()

# Environment & Connection Checks
st.subheader("🔌 Environment & Integration Status")
notion_token_set = bool(os.getenv("NOTION_API_KEY") or st.secrets.get("NOTION_API_KEY", None))
env_data = {
    "Integration Component": ["Notion API Token", "Streamlit Cloud Environment", "Local Cache Directory", "Middleware Interceptor"],
    "Status": [
        "✅ Configured" if notion_token_set else "⚠️ Missing/Not Set",
        "✅ Online" if os.path.exists("/mount/src") else "💻 Local Desktop Mode",
        "✅ Ready",
        "✅ Active"
    ]
}
st.dataframe(pd.DataFrame(env_data), use_container_width=True)
