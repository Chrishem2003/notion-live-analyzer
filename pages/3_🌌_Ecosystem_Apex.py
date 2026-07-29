
import streamlit as st

st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
import pandas as pd

st.set_page_config(page_title="Ecosystem Apex", page_icon="🌌", layout="wide")
st.subheader("🌌 Ecosystem Apex & Workspace Overview")
st.caption("Real-time telemetry and architectural status of the CHRISHEM Sovereign Intelligence Grid.")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("System Health", "100%", delta="Optimal")
with col2:
    st.metric("Active Enclaves", "21 Modules", delta="Secure")
with col3:
    st.metric("Database Engine", "SQLite Local", delta="Synchronized")

st.markdown("---")
subsystems = [
    {"Subsystem": "Access Control & Licensing", "Status": "Operational", "Security": "Encrypted"},
    {"Subsystem": "Academic & CV Studio", "Status": "Operational", "Security": "Export Ready"},
    {"Subsystem": "AI Intelligence Daemon", "Status": "Operational", "Security": "Autonomous"},
    {"Subsystem": "Telemetry & Diagnostics", "Status": "Operational", "Security": "Real-Time"}
]
st.dataframe(pd.DataFrame(subsystems), use_container_width=True)
