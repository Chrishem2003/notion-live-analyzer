import streamlit as st
import os
from datetime import datetime
import zoneinfo

# Page Configuration
st.set_page_config(
    page_title="Notion Live Research Analyzer",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 1. NATIVE BROWSER TIMEZONE & HOUR AUTO-DETECTION
# ---------------------------------------------------------
# Extract timezone or local hour passed from browser URL query params
query_params = st.query_params

if "tz" in query_params:
    st.session_state["user_tz"] = query_params["tz"]
if "local_hour" in query_params:
    try:
        st.session_state["local_hour"] = int(query_params["local_hour"])
    except ValueError:
        pass

# Fallback defaults if URL params are not yet set on first load
if "user_tz" not in st.session_state:
    st.session_state["user_tz"] = "UTC"
if "local_hour" not in st.session_state:
    st.session_state["local_hour"] = datetime.now().hour

# Non-blocking client-side script to detect browser time and update URL params smoothly
st.components.v1.html(
    """
    <script>
        const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const localHour = new Date().getHours();
        const urlParams = new URLSearchParams(window.parent.location.search);
        
        if (urlParams.get('tz') !== userTz || urlParams.get('local_hour') !== String(localHour)) {
            urlParams.set('tz', userTz);
            urlParams.set('local_hour', localHour);
            window.parent.location.search = urlParams.toString();
        }
    </script>
    """,
    height=0,
    width=0
)

active_tz_name = st.session_state["user_tz"]
local_hour = st.session_state["local_hour"]

# Compute formatted time string using detected timezone
try:
    tz = zoneinfo.ZoneInfo(active_tz_name)
    user_now = datetime.now(tz)
    formatted_time = user_now.strftime("%I:%M %p")
    formatted_date = user_now.strftime("%A, %B %d, %Y")
except Exception:
    user_now = datetime.now()
    formatted_time = user_now.strftime("%I:%M %p")
    formatted_date = user_now.strftime("%A, %B %d, %Y")

# Safe imports for internal modules
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
# 2. SIDEBAR: BRANDING, DYNAMIC LOCATION & NOTION CONNECTOR
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

    # Time Zone & Auto-Detected Location Status
    st.subheader("🌍 Dynamic Location Sync")
    st.success(f"📍 **Detected Timezone:** `{active_tz_name}`")
    st.caption(f"🕒 **Local Time:** {formatted_time}")

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
        
        if "db_ids" not in st.session_state or st.button("🔄 Force Re-sync Workspace", use_container_width=True):
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

    st.markdown("---")

    # Admin Portal Controls
    with st.expander("⚙️ Admin & User Management"):
        st.write("**Role:** System Administrator")
        admin_mode = st.toggle("Enable Admin Override", value=st.session_state.get("admin_mode", False))
        st.session_state["admin_mode"] = admin_mode

# ---------------------------------------------------------
# 3. ACCURATE REAL-TIME GREETING & DASHBOARD
# ---------------------------------------------------------

# Greeting calculation based on the user's detected local browser hour
if 5 <= local_hour < 12:
    greeting = "Good Morning ☀️"
elif 12 <= local_hour < 17:
    greeting = "Good Afternoon 🌤️"
elif 17 <= local_hour < 22:
    greeting = "Good Evening 🌙"
else:
    greeting = "Good Night 🌌"

# Header Display
st.markdown(f"# {greeting}, Welcome Back!")
st.caption(f"📅 {formatted_date} | 🕒 {formatted_time} ({active_tz_name})")

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
        st.info("Select a page from the sidebar navigation menu.")

st.markdown("---")

# Automated Health Monitor Cards
st.markdown("### 📊 Automated Workspace Health Monitor")
m_col1, m_col2, m_col3, m_col4 = st.columns(4)

with m_col1:
    st.metric(label="System Status", value="Online ⚡", delta="Global Sync")

with m_col2:
    detected_count = len(st.session_state.get("db_ids", {}))
    st.metric(label="Active Notion DBs", value=f"{detected_count}/5", delta="Synced")

with m_col3:
    st.metric(label="User Timezone", value=active_tz_name.split('/')[-1], delta=formatted_time)

with m_col4:
    admin_status = "Active" if st.session_state.get("admin_mode", False) else "Standard"
    st.metric(label="Admin Status", value=admin_status)

if "watermark" in globals():
    watermark()
