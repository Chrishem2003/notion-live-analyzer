import streamlit as st
import os
from datetime import datetime
import plotly.express as px

# 1. Page Configuration
st.set_page_config(
    page_title="Notion Live Research Analyzer",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import local modules safely
try:
    from modules.config import init_session_state, APP_DIR
    from modules.ui_components import hero_card, load_css, watermark
    from notion_helper import auto_detect_database_ids
except Exception as e:
    # Safe fallback if helper/modules are initializing
    pass

# Initialize session state tracking
if "init_session_state" in globals():
    init_session_state()

# Load custom CSS styling & theme if available
if "load_css" in globals():
    try:
        load_css()
    except Exception:
        pass

# ---------------------------------------------------------
# SIDEBAR: DP BRANDING, ADMIN & NOTION CONNECTION
# ---------------------------------------------------------
with st.sidebar:
    # Display Profile DP / App Logo
    logo_path = os.path.join("assets", "app_logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.title("🧬 Research Hub")

    st.markdown("## Notion Live Analyzer")
    st.caption("⚡ Advanced Research Analytics & Workspace Sync")
    st.markdown("---")

    # Notion Workspace Authentication
    st.subheader("🔑 Workspace Integration")
    notion_token = st.text_input(
        "Notion Access Token",
        type="password",
        value=st.session_state.get("notion_token", ""),
        help="Paste your integration token here"
    )

    REQUIRED_DATABASES = [
        "Project Master",
        "Genomic Sequence Log",
        "Literature Pipeline",
        "Sample Collections",
        "Bio-Acoustics Data"
    ]

    if notion_token:
        st.session_state["notion_token"] = notion_token
        if st.button("🔍 Auto-Detect Workspace DBs", use_container_width=True):
            with st.spinner("Scanning Notion workspace..."):
                try:
                    db_map = auto_detect_database_ids(notion_token, REQUIRED_DATABASES)
                    st.session_state["db_ids"] = db_map
                except NameError:
                    st.error("Auto-detect helper module is loading...")

    # Display Auto-Detected Status
    if "db_ids" in st.session_state:
        db_map = st.session_state["db_ids"]
        found = len(db_map)
        total = len(REQUIRED_DATABASES)
        if found == total:
            st.success(f" Connected: {found}/{total} DBs Found")
        else:
            st.warning(f" Syncing: {found}/{total} DBs Found")

    st.markdown("---")

    # Quick Admin & User Management Expandable Portal
    with st.expander("⚙️ Admin & User Management"):
        st.write("**Role:** System Administrator")
        st.caption("Manage user permissions and integration tokens.")
        admin_mode = st.toggle("Enable Admin Controls", value=st.session_state.get("admin_mode", False))
        st.session_state["admin_mode"] = admin_mode
        if admin_mode:
            st.info("Admin Mode Active: Full read/write overrides enabled.")

# ---------------------------------------------------------
# MAIN CONTENT: AUTO GREETING & HERO DASHBOARD
# ---------------------------------------------------------

# Dynamic Time-based Auto Greeting
current_hour = datetime.now().hour
if current_hour < 12:
    greeting = "Good Morning ☀️"
elif 12 <= current_hour < 17:
    greeting = "Good Afternoon 🌤️"
else:
    greeting = "Good Evening 🌙"

# Main Greeting Display
st.markdown(f"# {greeting}, Welcome Back!")
st.markdown("#### *Notion Live Research Analyzer & Intelligence Dashboard*")

st.markdown("---")

# Quick Access Action Buttons
st.markdown("### ⚡ Quick Access Actions")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🚀 Application Pipeline", use_container_width=True):
        st.switch_page("pages/46_📋_Application_Pipeline.py")

with col2:
    if st.button("💬 Text Analysis", use_container_width=True):
        st.switch_page("pages/11_💬_Text_Analysis.py")

with col3:
    if st.button("📑 APA Formatter", use_container_width=True):
        st.switch_page("pages/15_📑_APA_Outputs.py")

with col4:
    if st.button("📊 Database Metrics", use_container_width=True):
        st.info("Select a page from the sidebar navigation menu to view specific metrics.")

st.markdown("---")

# Visual Analytics Showcase Section
m_col1, m_col2, m_col3 = st.columns(3)
with m_col1:
    st.metric(label="Active Projects", value="12", delta="+2 this week")
with m_col2:
    st.metric(label="Genomic Sequences Logged", value="1,480", delta="+120 synced")
with m_col3:
    st.metric(label="Workspace Status", value="Connected" if "db_ids" in st.session_state else "Pending Sync")

# Bottom Watermark / Signature
if "watermark" in globals():
    watermark()
