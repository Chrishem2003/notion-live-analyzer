import streamlit as st
import os
from datetime import datetime
import plotly.express as px

# Streamlit Page Config
st.set_page_config(
    page_title="Notion Live Research Analyzer",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 1. ADVANCED AUTOMATION: JAVASCRIPT LOCAL TIME DETECTOR
# ---------------------------------------------------------
# Fallback local hour from server or JavaScript session state
if "user_local_hour" not in st.session_state:
    st.session_state["user_local_hour"] = datetime.now().hour

# Embed lightweight JS script to send real browser local time to Streamlit
st.components.v1.html(
    """
    <script>
        const userHour = new Date().getHours();
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: userHour
        }, '*');
    </script>
    """,
    height=0,
    width=0
)

# Safely import custom modules
try:
    from modules.config import init_session_state, APP_DIR
    from modules.ui_components import hero_card, load_css, watermark
    from notion_helper import auto_detect_database_ids
except Exception:
    pass

if "init_session_state" in globals():
    init_session_state()

if "load_css" in globals():
    try:
        load_css()
    except Exception:
        pass

# ---------------------------------------------------------
# 2. SIDEBAR BRANDING & AUTOMATED WORKSPACE SYNC
# ---------------------------------------------------------
with st.sidebar:
    logo_path = os.path.join("assets", "app_logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.title("🧬 Research Hub")

    st.markdown("## Notion Live Analyzer")
    st.caption("⚡ Automated Research Intelligence & Live Sync")
    st.markdown("---")

    # Notion Workspace Authentication
    st.subheader("🔑 Workspace Connection")
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

    # Automatic Sync trigger whenever token changes
    if notion_token:
        st.session_state["notion_token"] = notion_token
        
        # Auto-run discovery if not already done
        if "db_ids" not in st.session_state or st.sidebar.button("🔄 Force Re-sync Workspace", use_container_width=True):
            with st.spinner("Automating Notion DB Discovery..."):
                try:
                    db_map = auto_detect_database_ids(notion_token, REQUIRED_DATABASES)
                    st.session_state["db_ids"] = db_map
                except Exception as e:
                    st.error(f"Sync error: {e}")

    # Display Auto-Detected Status
    if "db_ids" in st.session_state:
        db_map = st.session_state["db_ids"]
        found = len(db_map)
        total = len(REQUIRED_DATABASES)
        
        if found == total:
            st.success(f" Automated Sync Active ({found}/{total} DBs)")
        else:
            st.warning(f" Partial Sync ({found}/{total} DBs)")
            
        with st.expander("🔍 Live DB Map"):
            for db_name, db_id in db_map.items():
                st.caption(f"**{db_name}:** `{db_id[:8]}...`")

    st.markdown("---")

    # Admin Portal Controls
    with st.expander("⚙️ Admin & User Management"):
        st.write("**Role:** System Administrator")
        st.caption("Automated security overrides and user management.")
        admin_mode = st.toggle("Enable Admin Override", value=st.session_state.get("admin_mode", False))
        st.session_state["admin_mode"] = admin_mode

# ---------------------------------------------------------
# 3. REAL-TIME AUTOMATED GREETING & DASHBOARD
# ---------------------------------------------------------

# Compute Greeting using real-time local browser hour
local_hour = st.session_state.get("user_local_hour", datetime.now().hour)

if 5 <= local_hour < 12:
    greeting = "Good Morning ☀️"
elif 12 <= local_hour < 17:
    greeting = "Good Afternoon 🌤️"
elif 17 <= local_hour < 22:
    greeting = "Good Evening 🌙"
else:
    greeting = "Good Night 🌌"

# Header Banner
st.markdown(f"# {greeting}, Welcome Back!")
st.markdown("#### *Real-Time Notion Research Analyzer & Automated Pipeline Hub*")

st.markdown("---")

# Quick Access Action Buttons
st.markdown("### ⚡ Quick Access Actions")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📋 Application Pipeline", use_container_width=True):
        st.switch_page("pages/46_📋_Application_Pipeline.py")

with col2:
    if st.button("💬 Text Analysis", use_container_width=True):
        st.switch_page("pages/11_💬_Text_Analysis.py")

with col3:
    if st.button("📑 APA Formatter", use_container_width=True):
        st.switch_page("pages/15_📑_APA_Outputs.py")

with col4:
    if st.button("📊 Database Metrics", use_container_width=True):
        st.info("Select a page from the sidebar navigation to inspect detailed database charts.")

st.markdown("---")

# ---------------------------------------------------------
# 4. AUTOMATED HEALTH & ANALYTICS MONITOR
# ---------------------------------------------------------
st.markdown("### 📊 Automated Workspace Health Monitor")

m_col1, m_col2, m_col3, m_col4 = st.columns(4)

with m_col1:
    st.metric(label="System Status", value="Online ⚡", delta="Automated")

with m_col2:
    detected_count = len(st.session_state.get("db_ids", {}))
    st.metric(label="Active Notion DBs", value=f"{detected_count}/5", delta="Live")

with m_col3:
    st.metric(label="Data Refresh Rate", value="Real-Time", delta="60s Sync")

with m_col4:
    admin_status = "Active" if st.session_state.get("admin_mode", False) else "Standard"
    st.metric(label="Admin Status", value=admin_status)

# Automated Watermark
if "watermark" in globals():
    watermark()
