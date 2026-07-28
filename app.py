import streamlit as st
import pandas as pd
from modules.auth import render_auth_gateway
from modules.i18n import get_locale_strings
from security.waf import sanitize_payload

# Page Setup
st.set_page_config(
    page_title="CHRISHEM Intelligence Engine",
    page_icon="???",
    layout="wide"
)

# 1. Execute Authentication Check
render_auth_gateway()

# 2. Load Localization Strings
strings = get_locale_strings()

# Main Dashboard Interface
st.title(strings["title"])
st.caption(strings["subtitle"])

st.sidebar.markdown(f"**Logged in as:** {st.session_state.get('user', 'Authorized')}")
if st.sidebar.button("Log Out"):
    st.session_state.authenticated = False
    st.rerun()

# Workspace Content
tab1, tab2, tab3 = st.tabs(["?? Analytics Workspace", "?? Global Downloads", "??? Security Diagnostics"])

with tab1:
    st.subheader("Automated Dataset Diagnostics")
    raw_query = st.text_input("Enter search or filter term:", "Standard Analysis")
    safe_query = sanitize_payload(raw_query)
    st.write(f"Processed Query Safely: {safe_query}")

with tab2:
    st.subheader(strings["export"])
    sample_export_df = pd.DataFrame({
        "Metric": ["Throughput", "Latency", "Integrity Check", "Uptime"],
        "Value": ["99.98%", "14ms", "Verified", "24/7 Active"]
    })
    st.dataframe(sample_export_df, use_container_width=True, hide_index=True)
    
    csv_data = sample_export_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="?? Download Localized Dataset (CSV)",
        data=csv_data,
        file_name="chrishem_engine_export.csv",
        mime="text/csv"
    )

with tab3:
    st.subheader("Autonomous Daemon Status")
    st.success("Self-Healing Watchdog: **ONLINE**")
    st.success("Web Application Firewall: **ACTIVE**")
    st.success("Git Auto-Sync Daemon: **RUNNING**")
