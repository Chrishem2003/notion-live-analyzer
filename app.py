import streamlit as st
import os
from datetime import datetime
import zoneinfo
from streamlit_autorefresh import st_autorefresh

# Page Configuration
st.set_page_config(
    page_title="Notion Live Research Analyzer",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# CUSTOM CSS FOR SIDEBAR SCROLLING & UI STYLING
# ---------------------------------------------------------
st.markdown("""
    <style>
        /* Force scrollbar on Streamlit sidebar */
        [data-testid="stSidebar"] > div:first-child {
            overflow-y: auto !important;
            max-height: 100vh !important;
        }
        /* Custom scrollbar styling */
        [data-testid="stSidebar"]::-webkit-scrollbar {
            width: 6px;
        }
        [data-testid="stSidebar"]::-webkit-scrollbar-thumb {
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: 3px;
        }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. SILENT AUTO-REFRESH CLOCK (Updates every 10 seconds)
# ---------------------------------------------------------
# Silent background refresh keeping local time accurate without interrupting typing
count = st_autorefresh(interval=10000, limit=None, key="time_counter")

# Timezone & State Initialization (Autosaved in st.session_state)
COMMON_TIMEZONES = [
    "Africa/Kampala",
    "UTC",
    "Africa/Nairobi",
    "Europe/London",
    "America/New_York",
    "America/Los_Angeles",
    "Asia/Tokyo",
    "Asia/Dubai"
]

if "user_tz" not in st.session_state:
    st.session_state["user_tz"] = "Africa/Kampala"

active_tz_name = st.session_state["user_tz"]

# Compute real-time hour and formatted date/time strings
try:
    tz = zoneinfo.ZoneInfo(active_tz_name)
    user_now = datetime.now(tz)
except Exception:
    user_now = datetime.now()

local_hour = user_now.hour
formatted_time = user_now.strftime("%I:%M:%S %p")
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
# 2. SIDEBAR WITH SCROLLING, TIMEZONE & NOTION CONTROLS
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

    # Timezone Selector with Real-time Clock
    st.subheader("🌍 Timezone & Location")
    st.success(f"🕒 **Live Local Time:** `{formatted_time}`")
    
    selected_tz = st.selectbox(
        "Select Your Location / Timezone:",
        options=COMMON_TIMEZONES,
        index=COMMON_TIMEZONES.index(active_tz_name) if active_tz_name in COMMON_TIMEZONES else 0,
        help="Choose your local timezone to adjust greetings and time metrics."
    )
    
    if selected_tz != st.session_state["user_tz"]:
        st.session_state["user_tz"] = selected_tz
        st.rerun()

    st.markdown("---")

    # Notion Workspace Authentication with Autosave
    st.subheader("🔑 Workspace Integration")
    notion_token = st.text_input(
        "Notion Access Token",
        type="password",
        value=st.session_state.get("notion_token", ""),
        help="Paste your integration token here (Autosaved)"
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
# 3. ACCURATE GREETING & DASHBOARD
# ---------------------------------------------------------

# Accurate Greeting based on current local hour
if 5 <= local_hour < 12:
    greeting = "Good Morning ☀️"
elif 12 <= local_hour < 17:
    greeting = "Good Afternoon 🌤️"
elif 17 <= local_hour < 22:
    greeting = "Good Evening 🌙"
else:
    greeting = "Good Night 🌌"

# Header Display with Live Clock
st.markdown(f"# {greeting}, Welcome Back!")
st.caption(f"📅 {formatted_date} | 🕒 **{formatted_time}** ({active_tz_name})")

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
    st.metric(label="System Status", value="Online ⚡", delta="Live Sync")

with m_col2:
    detected_count = len(st.session_state.get("db_ids", {}))
    st.metric(label="Active Notion DBs", value=f"{detected_count}/5", delta="Synced")

with m_col3:
    st.metric(label="Selected Timezone", value=active_tz_name.split('/')[-1], delta=formatted_time)

with m_col4:
    admin_status = "Active" if st.session_state.get("admin_mode", False) else "Standard"
    st.metric(label="Admin Status", value=admin_status)

if "watermark" in globals():
    watermark()
