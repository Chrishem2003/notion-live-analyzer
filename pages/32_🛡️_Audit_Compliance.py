"""
Audit & Compliance Hub — Standalone Secure Page
Provides forensic text analysis, AI-content detection, plagiarism checking,
text humanization, blockchain-verified audit trails, and multi-source document ingestion.
"""

import sys
from pathlib import Path

# ─── ULTIMATE PATH RESOLUTION ────────────────────────────────────────
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(current_file.parent) not in sys.path:
    sys.path.insert(0, str(current_file.parent))


import streamlit as st
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
import hashlib
from datetime import datetime

# ─── Page Configuration ───────────────────────────────────────────────
st.set_page_config(
    page_title="Audit & Compliance Hub [SECURE]",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header
from modules.literature_engine import LiteratureDatabase
from modules.audit_ui import render_audit_tab

# ─── Initialization & Security Gate ───────────────────────────────────
init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

if "audit_clearance" not in st.session_state:
    st.session_state.audit_clearance = False

hero_card(
    "🛡️ Audit & Compliance Hub [CLASSIFIED]",
    "Multi-vector forensic text analysis, blockchain-verified audit trails, "
    "local device browser ingestion, and advanced research compliance screening.",
    badge_text="🔒 Restricted Access Hub"
)
watermark("CHRISHEM")

# ─── Initialize Database ─────────────────────────────────────────────
db = LiteratureDatabase()

# ─── Main View Control Center (Non-Sidebar Layout) ────────────────────
st.markdown("---")

col_sec, col_proj = st.columns([1, 1])

with col_sec:
    st.markdown("### 🔐 Security & Access Control")
    security_input = st.text_input("Enter Access Passkey", type="password", placeholder="••••••••", key="main_passkey_input")
    if security_input:
        if security_input == "CHRISHEM" or hashlib.sha256(security_input.encode()).hexdigest() == hashlib.sha256(b"CHRISHEM").hexdigest():
            st.session_state.audit_clearance = True
            st.success("✅ Clearance Granted: Level-1 Admin")
        else:
            st.error("❌ Access Denied: Invalid Passkey")
            st.session_state.audit_clearance = False

with col_proj:
    st.markdown("### 📚 Research Project & Sources")
    source_mode = st.radio(
        "Select Ingestion Vector",
        ["Literature Engine Database", "Local Device Browser (PDF/TXT)"],
        horizontal=True
    )

project_id = None

if source_mode == "Literature Engine Database":
    projects = db.get_projects()
    if not projects:
        st.info("No projects found in Literature Engine. Switch to Local Ingestion or create one.")
        project_options = {0: "➕ Create New Project"}
    else:
        project_options = {p["id"]: f"📖 {p['name']}" for p in projects}
        project_options[0] = "➕ Create New Project"

    selected_option = st.selectbox(
        "Select Active Research Project",
        options=list(project_options.keys()),
        format_func=lambda x: project_options.get(x, f"Project #{x}"),
        key="audit_standalone_project",
    )

    if selected_option == 0:
        st.warning("⚠️ **Select a valid project above** or upload local files to begin auditing.")
        st.stop()

    project_id = selected_option
    project = db.get_project(project_id)
    if project:
        col_m1, col_m2, col_m3 = st.columns(3)
        stats = db.get_statistics(project_id)
        col_m1.metric("📊 Total Database Papers", stats["total_papers"])
        col_m2.metric("✅ Checked Papers", stats["checked_papers"])
        col_m3.metric("🔖 Cited in Report", stats.get("cited_papers", 0))

else:
    st.markdown("### 📂 Local Browser Ingestion")
    uploaded_files = st.file_uploader(
        "Grab papers from device browser",
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True,
        help="Upload reference literature directly from your local filesystem for instant parsing."
    )
    
    if uploaded_files:
        st.success(f"📂 Loaded {len(uploaded_files)} local document(s) successfully.")
        project_id = -999 
        st.session_state["local_audit_files"] = uploaded_files
    else:
        st.warning("⚠️ No local documents uploaded yet.")
        st.stop()

st.markdown("---")

# ─── Main Content — Render Classified Audit UI ────────────────────────
if project_id == -999:
    section_header("Local Ingestion Forensic Workspace", "Analyzing files grabbed directly from device storage.")
    st.markdown(f"**Active Security Clearance:** {'🔓 Active (CHRISHEM)' if st.session_state.audit_clearance else '🔒 Locked (Restricted)'}")
    
    local_files = st.session_state.get("local_audit_files", [])
    st.info(f"Ready to process {len(local_files)} local document(s) through multi-vector verification.")
    
    render_audit_tab(db, project_id, local_sources=local_files, clearance=st.session_state.audit_clearance)
else:
    render_audit_tab(db, project_id, clearance=st.session_state.audit_clearance)

# ─── Footer Timestamp ─────────────────────────────────────────────────
st.markdown("---")
st.caption(f"🛡️ Audit & Compliance Hub | System Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EAT")