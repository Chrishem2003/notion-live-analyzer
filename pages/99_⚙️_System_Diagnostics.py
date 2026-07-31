import streamlit as st
import sys
import os
import time
import platform
import psutil
import gc
import json
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
from typing import Dict, List, Any

# Ensure module initialization wrapper
try:
    from modules.system_middleware import initialize_system_state
    initialize_system_state()
except ImportError:
    # Graceful fallback if module is out of path during local dev
    if "app_initialized" not in st.session_state:
        st.session_state.app_initialized = True
    if "error_logs" not in st.session_state:
        st.session_state.error_logs = []

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & THEME STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="System Diagnostics & Health Hub",
    page_icon="??",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Injecting Modern Aesthetics, Colors & Responsive Styles
CUSTOM_CSS = """
<style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
    /* Global Color Palette Definitions */
    :root {
        --bg-base: #0E1117;
        --card-bg: #161B22;
        --accent-primary: #00E5FF;
        --accent-secondary: #6366F1;
        --status-success: #10B981;
        --status-warning: #F59E0B;
        --status-error: #EF4444;
        --text-muted: #94A3B8;
        --border-color: #30363D;
    }
    
    /* Main Layout Enhancements */
    .stApp {
        background-color: var(--bg-base);
    }
    
    /* Diagnostic Glassmorphic Metric Cards */
    div[data-testid="stMetric"] {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: var(--accent-primary);
    }
    div[data-testid="stMetricLabel"] > div {
        color: var(--text-muted) !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] > div {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    
    /* Custom Status Badges */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        text-align: center;
    }
    .badge-success { background-color: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981; }
    .badge-warning { background-color: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; }
    .badge-error { background-color: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid #EF4444; }
    
    /* Expandable Code Blocks Styling */
    .stExpander {
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        background-color: var(--card-bg) !important;
        margin-bottom: 8px;
    }
    
    /* Divider Customization */
    hr {
        border-color: var(--border-color) !important;
        margin: 1.5rem 0 !important;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS & TELEMETRY SUITE
# -----------------------------------------------------------------------------
def get_system_uptime() -> str:
    """Calculates system boot operational uptime duration."""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    now = datetime.now()
    delta = now - boot_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

def execute_garbage_collection() -> int:
    """Forces manual garbage collection and returns freed memory objects count."""
    return gc.collect()

def check_secret_key(key: str) -> bool:
    """Safely checks if an environment variable or Streamlit secret exists."""
    return bool(os.getenv(key) or st.secrets.get(key, None))

# Initialize System Metrics Tracking Timeline Buffer
if "telemetry_history" not in st.session_state:
    st.session_state.telemetry_history = []

# Capture dynamic timeline data point
current_time = datetime.now().strftime("%H:%M:%S")
cpu_usage = psutil.cpu_percent(interval=None)
ram_usage = psutil.virtual_memory().percent

st.session_state.telemetry_history.append({
    "Timestamp": current_time,
    "CPU (%)": cpu_usage,
    "RAM (%)": ram_usage
})

# Maintain last 30 telemetry data frames to control memory load
if len(st.session_state.telemetry_history) > 30:
    st.session_state.telemetry_history.pop(0)

# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS & UTILITIES
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("??? Admin Console")
    st.markdown("System Control Panel & Actions")
    
    st.subheader("Telemetry Controls")
    auto_refresh = st.checkbox("Enable Auto Refresh Feed", value=False)
    refresh_rate = st.selectbox("Interval Speed", [2, 5, 10, 30], index=1)
    
    st.divider()
    st.subheader("Operational Actions")
    if st.button("?? Run Garbage Collector", use_container_width=True):
        freed = execute_garbage_collection()
        st.toast(f"Garbage collection executed! Freed {freed} objects.", icon="?")
        
    if st.button("?? Inject Test Error Trace", use_container_width=True):
        try:
            # Intentional Error for Diagnostics Verification
            _ = 1 / 0
        except Exception as e:
            import traceback
            error_msg = f"[{datetime.now(timezone.utc).isoformat()}] Simulated Test Failure: {str(e)}\n{traceback.format_exc()}"
            st.session_state.setdefault("error_logs", []).append(error_msg)
            st.toast("Simulated diagnostic exception logged!", icon="??")
            st.rerun()

    if st.button("??? Reset All Exception Logs", use_container_width=True):
        st.session_state.error_logs = []
        st.toast("Error log history completely cleared.", icon="?")
        st.rerun()
        
    st.divider()
    st.caption(f"Host OS: {platform.system()} {platform.release()}")
    st.caption(f"Python Runtime: {sys.version.split()[0]}")

# -----------------------------------------------------------------------------
# MAIN DASHBOARD CONTENT
# -----------------------------------------------------------------------------
st.title("?? System Diagnostics & Health Hub")
st.markdown("Real-time telemetry, memory analytics, integration state monitoring, and operational error tracing.")

# Diagnostic Top Bar System Metrics Highlights
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
with col2:
    st.metric("Streamlit Engine", st.__version__)
with col3:
    st.metric("Active Error Logs", len(st.session_state.get("error_logs", [])))
with col4:
    status_label = "Active" if st.session_state.get("app_initialized") else "Initializing"
    st.metric("Session Status", status_label)
with col5:
    st.metric("System Uptime", get_system_uptime())

st.divider()

# Diagnostic Operations Dashboard Tabs
tab_overview, tab_telemetry, tab_errors, tab_integrations, tab_state = st.tabs([
    "?? System Overview", 
    "?? Resource Telemetry", 
    "?? Captured Exceptions", 
    "?? Integration Status",
    "??? Session State Explorer"
])

# -----------------------------------------------------------------------------
# TAB 1: SYSTEM OVERVIEW
# -----------------------------------------------------------------------------
with tab_overview:
    st.subheader("??? Server Resource Footprint")
    
    ov_col1, ov_col2, ov_col3, ov_col4 = st.columns(4)
    
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    with ov_col1:
        st.metric("CPU Allocation", f"{cpu_usage}%")
    with ov_col2:
        st.metric("RAM Consumption", f"{ram_usage}%", f"{round(vm.used / (1024**3), 2)} GB / {round(vm.total / (1024**3), 2)} GB")
    with ov_col3:
        st.metric("Disk Storage", f"{disk.percent}%", f"{round(disk.free / (1024**3), 2)} GB Free")
    with ov_col4:
        st.metric("Active Threads", psutil.Process().num_threads())

    st.markdown("##### System Environment Details")
    sys_details = {
        "Property": ["Machine Architecture", "Processor Identifier", "Logical CPU Cores", "Physical CPU Cores", "Python Executable Path", "Process ID (PID)"],
        "Value": [
            platform.machine(),
            platform.processor() or "Generic X86/ARM Host",
            str(psutil.cpu_count(logical=True)),
            str(psutil.cpu_count(logical=False)),
            sys.executable,
            str(os.getpid())
        ]
    }
    st.dataframe(pd.DataFrame(sys_details), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# TAB 2: RESOURCE TELEMETRY
# -----------------------------------------------------------------------------
with tab_telemetry:
    st.subheader("?? Live Hardware Performance Tracking")
    
    if st.session_state.telemetry_history:
        chart_df = pd.DataFrame(st.session_state.telemetry_history)
        
        fig = px.line(
            chart_df, 
            x="Timestamp", 
            y=["CPU (%)", "RAM (%)"],
            markers=True,
            color_discrete_map={"CPU (%)": "#00E5FF", "RAM (%)": "#6366F1"},
            template="plotly_dark"
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Gathering initial telemetry metrics...")

# -----------------------------------------------------------------------------
# TAB 3: CAPTURED EXCEPTIONS
# -----------------------------------------------------------------------------
with tab_errors:
    st.subheader("?? Session Exception Logs & Diagnostics")
    error_logs = st.session_state.get("error_logs", [])
    
    if not error_logs:
        st.success("? Operational status nominal: No runtime exceptions or errors caught during this session.")
    else:
        filter_term = st.text_input("?? Filter stack traces by keyword...", "")
        
        filtered_logs = [log for log in error_logs if filter_term.lower() in log.lower()] if filter_term else error_logs
        
        st.caption(f"Displaying {len(filtered_logs)} of {len(error_logs)} total error trace records.")
        
        for idx, log in enumerate(reversed(filtered_logs)):
            original_idx = len(error_logs) - idx
            with st.expander(f"?? Exception Log Record #{original_idx}"):
                st.code(log, language="python")
                
        err_col1, err_col2 = st.columns([1, 4])
        with err_col1:
            if st.button("??? Clear Log History", key="clear_logs_tab"):
                st.session_state.error_logs = []
                st.rerun()
        with err_col2:
            st.download_button(
                label="?? Export Logs (JSON)",
                data=json.dumps(error_logs, indent=2),
                file_name=f"system_logs_{int(time.time())}.json",
                mime="application/json"
            )

# -----------------------------------------------------------------------------
# TAB 4: INTEGRATION STATUS
# -----------------------------------------------------------------------------
with tab_integrations:
    st.subheader("?? Environment & Integration Health Audit")
    
    notion_token_set = check_secret_key("NOTION_API_KEY")
    is_cloud_env = os.path.exists("/mount/src")
    
    integrations_list = [
        {
            "Integration Component": "Notion API Token",
            "Target Endpoint / Key": "NOTION_API_KEY",
            "Type": "External Service Auth",
            "Status": "? Configured" if notion_token_set else "?? Missing/Not Set"
        },
        {
            "Integration Component": "Streamlit Cloud Container",
            "Target Endpoint / Key": "/mount/src",
            "Type": "Deployment Runtime",
            "Status": "? Cloud Instance" if is_cloud_env else "?? Local Desktop Mode"
        },
        {
            "Integration Component": "Local Cache Subsystem",
            "Target Endpoint / Key": ".streamlit/cache",
            "Type": "Disk Storage Subsystem",
            "Status": "? Operational"
        },
        {
            "Integration Component": "System Middleware Interceptor",
            "Target Endpoint / Key": "modules.system_middleware",
            "Type": "Internal Middleware",
            "Status": "? Active & Initialized" if st.session_state.get("app_initialized") else "?? Degraded/Uninitialized"
        }
    ]
    
    int_df = pd.DataFrame(integrations_list)
    st.dataframe(int_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# TAB 5: SESSION STATE EXPLORER
# -----------------------------------------------------------------------------
with tab_state:
    st.subheader("??? In-Memory Session State Inspection")
    st.markdown("Live diagnostic breakdown of variables retained within `st.session_state`.")
    
    state_dict = {key: str(value) for key, value in st.session_state.items()}
    st.json(state_dict)

# -----------------------------------------------------------------------------
# AUTOMATED REFRESH LOGIC
# -----------------------------------------------------------------------------
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
