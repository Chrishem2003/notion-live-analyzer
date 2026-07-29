import streamlit as st
import pandas as pd
import os
from modules.auth import render_auth_gateway
from modules.i18n import get_locale_strings
from security.waf import sanitize_payload
from modules.database import init_db, save_user_session, log_backend_event
from modules.vault import render_secure_vault
from modules.analytics import render_advanced_analytics
from modules.webhook import dispatch_system_alert
from modules.db_viewer import render_database_audit_logs
from modules.executive import render_executive_summary
from modules.health_monitor import render_health_monitor
from modules.report_generator import render_report_exporter
from modules.data_cleaner import render_data_cleaner

# Initialize Persistent Backend Database
init_db()

# Page Configuration Setup
st.set_page_config(
    page_title="CHRISHEM Intelligence Engine",
    page_icon="???",
    layout="wide"
)

# Load Custom Styling Sheet
if os.path.exists("assets/style.css"):
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Execute Authentication Check
render_auth_gateway()

current_user = st.session_state.get('user', 'Authorized')
current_lang = st.session_state.get('global_lang_select', 'English')
save_user_session(current_user, "Active Gateway", current_lang)

strings = get_locale_strings()

st.title(strings["title"])
st.caption(strings["subtitle"])

st.sidebar.markdown(f"**Logged in as:** {current_user}")
if st.sidebar.button("Log Out"):
    log_backend_event("INFO", f"User {current_user} logged out.")
    st.session_state.authenticated = False
    st.rerun()

# Webhook Alert Configuration in Sidebar
with st.sidebar.expander("?? Webhook Alerts"):
    wh_url = st.text_input("Webhook Endpoint URL", "https://your-webhook-endpoint")
    if st.button("Test Webhook Alert"):
        success = dispatch_system_alert(wh_url, f"Manual test alert from user {current_user}")
        if success:
            st.toast("Webhook notification dispatched!", icon="??")
        else:
            st.error("Failed to reach webhook endpoint.")

# Unified Multi-Tab Enterprise Architecture (Expanded to 8 Tabs)
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "?? Executive Summary",
    "?? Analytics Workspace", 
    "?? Bioinformatics Engine", 
    "?? Dataset Cleaner",
    "?? Secure Vault", 
    "??? Database Logs",
    "?? Global Downloads", 
    "??? System Diagnostics"
])

with tab1:
    render_executive_summary()

with tab2:
    st.subheader("Automated Dataset Diagnostics")
    raw_query = st.text_input("Enter search or filter term:", "Standard Analysis")
    safe_query = sanitize_payload(raw_query)
    st.write(f"Processed Query Safely: {safe_query}")
    log_backend_event("INFO", f"Executed safe query lookup: {safe_query}")

with tab3:
    render_advanced_analytics()

with tab4:
    render_data_cleaner()

with tab5:
    render_secure_vault()

with tab6:
    render_database_audit_logs()

with tab7:
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
    
    st.markdown("---")
    render_report_exporter()

with tab8:
    render_health_monitor()
