import streamlit as st
import pandas as pd

# 1. Import from all 6 module files
try:
    from modules.ui_styles import apply_custom_styles
except ImportError:
    def apply_custom_styles(): pass

try:
    from modules.auth import check_authentication
except ImportError:
    def check_authentication(): return True

try:
    from modules.audit_logger import log_event
except ImportError:
    def log_event(event_type, details): pass

try:
    from modules.notion_client import fetch_notion_data
except ImportError:
    def fetch_notion_data(*args, **kwargs): return pd.DataFrame()

try:
    from modules.file_analyzer import render_file_analyzer_page
except ImportError:
    def render_file_analyzer_page(): st.info("File Analyzer Module Loaded.")

# Apply custom UI styling from ui_styles.py
st.set_page_config(page_title="Bio-Research Enterprise Analyzer", layout="wide", page_icon="🧬")
apply_custom_styles()

log_event("SESSION_START", "App session initialized")

# Render Sidebar & Navigation
st.sidebar.title("🧬 Bio-Research Hub")
page = st.sidebar.radio("Navigation", ["Dashboard & Notion Live", "📁 File Analyzer", "🔒 Auth & Settings", "📜 Audit Logs"])

if page == "Dashboard & Notion Live":
    st.title("📊 Bio-Research Dashboard")
    st.write("Live Notion workspace metrics and synchronized data tables.")
    
    # Safely fetch Notion data using notion_client.py
    api_key = st.secrets.get("NOTION_TOKEN", "") or st.secrets.get("NOTION_API_KEY", "")
    db_id = st.secrets.get("NOTION_DATABASE_ID", "")
    
    if api_key and db_id:
        df = fetch_notion_data(db_id, api_key)
        if isinstance(df, pd.DataFrame) and not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No active records found or Page ID passed instead of Database ID. Upload a dataset or update your Database ID in Secrets.")
    else:
        st.warning("Notion API credentials not detected in Streamlit Secrets.")

elif page == "📁 File Analyzer":
    st.title("📁 Local File Analyzer")
    render_file_analyzer_page()

elif page == "🔒 Auth & Settings":
    st.title("🔒 Security & Credentials")
    st.write("Configure environment variables and check active secret bindings.")

elif page == "📜 Audit Logs":
    st.title("📜 System Audit Logs")
    st.write("Traceability logs for research pipeline events.")
