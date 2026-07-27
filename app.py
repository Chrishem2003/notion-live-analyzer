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
# 1. TIMEZONE & STATE INITIALIZATION
# ---------------------------------------------------------
OWNER_EMAIL = "chrishem242@gmail.com"

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

if "is_owner" not in st.session_state:
    st.session_state["is_owner"] = False

active_tz_name = st.session_state["user_tz"]

def get_time_data(tz_name):
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
        user_now = datetime.now(tz)
    except Exception:
        user_now = datetime.now()
    
    local_hour = user_now.hour
    formatted_time = user_now.strftime("%I:%M:%S %p")
    formatted_date = user_now.strftime("%A, %B %d, %Y")
    
    if 5 <= local_hour < 12:
        greeting = "Good Morning ☀️"
    elif 12 <= local_hour < 17:
        greeting = "Good Afternoon 🌤️"
    elif 17 <= local_hour < 22:
        greeting = "Good Evening 🌙"
    else:
        greeting = "Good Night 🌌"
        
    return greeting, formatted_time, formatted_date

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
# 2. SIDEBAR WITH OWNER AUTHENTICATION & CONTROLS
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

    # Timezone Selector
    st.subheader("🌍 Timezone & Location")
    
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

    # Admin & Owner Portal
    with st.expander("🔐 Owner & Admin Portal"):
        if st.session_state["is_owner"]:
            st.success("👑 **Master Owner Unlocked**")
            st.caption(f"Authenticated as: `{OWNER_EMAIL}`")
            
            # Owner Overrides
            admin_mode = st.toggle("Enable Admin Override Mode", value=st.session_state.get("admin_mode", True))
            st.session_state["admin_mode"] = admin_mode
            
            if st.button("🔒 Lock Owner Portal", use_container_width=True):
                st.session_state["is_owner"] = False
                st.session_state["admin_mode"] = False
                st.rerun()
        else:
            st.write("**System Authentication**")
            input_email = st.text_input("Owner Email Address", key="admin_email_input")
            admin_pass = st.text_input("Master Key", type="password", key="admin_pass_input")
            
            if st.button("Verify Credentials", use_container_width=True):
                if input_email.strip().lower() == OWNER_EMAIL.lower():
                    st.session_state["is_owner"] = True
                    st.session_state["admin_mode"] = True
                    st.success("Access Granted! Owner Privileges Activated.")
                    st.rerun()
                else:
                    st.error("Unauthorized email address.")

# ---------------------------------------------------------
# 3. REAL-TIME AUTO-REFRESHING HEADER & DASHBOARD
# ---------------------------------------------------------

@st.fragment(run_every=5)
def render_live_header():
    current_tz = st.session_state.get("user_tz", "Africa/Kampala")
    greeting, formatted_time, formatted_date = get_time_data(current_tz)
    st.markdown(f"# {greeting}, Welcome Back!")
    st.caption(f"📅 {formatted_date} | 🕒 **{formatted_time}** ({current_tz})")

render_live_header()

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
    greeting, formatted_time, _ = get_time_data(active_tz_name)
    st.metric(label="Selected Timezone", value=active_tz_name.split('/')[-1], delta=formatted_time)

with m_col4:
    role_label = "👑 Master Owner" if st.session_state.get("is_owner") else "Standard User"
    st.metric(label="Account Privilege", value=role_label)

# ---------------------------------------------------------
# 4. OWNER-ONLY SYSTEM CONTROLS (Rendered if Unlocked)
# ---------------------------------------------------------
if st.session_state.get("is_owner"):
    st.markdown("---")
    st.markdown("## ⚙️ Master Owner Controls & Global Overrides")
    
    o_col1, o_col2, o_col3 = st.columns(3)
    
    with o_col1:
        st.subheader("🧹 System Cache & State")
        if st.button("Clear Application Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache cleared successfully!")
            
    with o_col2:
        st.subheader("📡 Workspace Sync Controls")
        if st.button("Force Global Re-index", use_container_width=True):
            st.info("Re-indexing database schemas...")
            
    with o_col3:
        st.subheader("📊 Global Analytics")
        st.write(f"**Registered Owner:** `{OWNER_EMAIL}`")
        st.write(f"**Session Active:** `{st.session_state['is_owner']}`")

if "watermark" in globals():
    watermark()
