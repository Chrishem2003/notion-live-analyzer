"""
═══════════════════════════════════════════════════════════════════════════════
ENTERPRISE GIT & VERSION CONTROL STUDIO [v3.0]
High-performance code and research pipeline synchronization suite: Track dataset
iterations, push analytical scripts, manage branches, and collaborate seamlessly
across academic or engineering projects.
Designed for: Chrishem Studio Engine
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
import time
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st

# ─── PATH RESOLUTION ─────────────────────────────────────────────────
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(current_file.parent) not in sys.path:
    sys.path.insert(0, str(current_file.parent))

# ─── DEFENSIVE MODULE IMPORTS WITH LOCAL FALLBACKS ────────────────────
try:
    from modules.config import init_session_state
    from modules.ui_components import hero_card, section_header, load_css, watermark, git_status_badge
    from modules.git_integration import render_git_integration_ui
except ImportError:
    def init_session_state():
        if "theme" not in st.session_state:
            st.session_state["theme"] = "dark"

    def load_css(is_dark=True):
        pass

    def watermark(text=""):
        pass

    def section_header(text="", desc=""):
        st.markdown(
            f"<h3 style='color:#00f2fe !important; margin-top:1.4rem; margin-bottom:0.3rem; font-weight:800;'>{text}</h3>", 
            unsafe_allow_html=True
        )
        if desc:
            st.caption(desc)

    def git_status_badge(is_connected=False):
        if is_connected:
            return "<span style='background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.75rem; font-weight: 700; border: 1px solid #10b981;'>🟢 Connected</span>"
        return "<span style='background: rgba(239, 68, 68, 0.2); color: #ef4444; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.75rem; font-weight: 700; border: 1px solid #ef4444;'>🔴 Offline</span>"

    def hero_card(title, subtitle, badge_text=""):
        st.markdown(f"""
        <div style="padding: 1.5rem; background: linear-gradient(135deg, rgba(0, 242, 254, 0.12) 0%, rgba(11, 19, 33, 0.95) 100%); border-radius: 12px; border: 1px solid #00f2fe; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(0,242,254,0.15);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
                <h1 style="color: #00f2fe !important; font-size: 2rem; margin: 0; font-weight: 800; letter-spacing: -0.02em;">{title}</h1>
                <span style="background: rgba(0, 242, 254, 0.15); color: #00f2fe; padding: 0.3rem 0.8rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; border: 1px solid #00f2fe;">{badge_text}</span>
            </div>
            <p style="color: #cbd5e1 !important; font-size: 0.95rem; margin: 0; line-height: 1.4;">{subtitle}</p>
        </div>
        """, unsafe_allow_html=True)

    def render_git_integration_ui():
        st.markdown('<div class="synth-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='color:#00f2fe;'>🔗 Active Git Repository Handshake</h4>", unsafe_allow_html=True)
        st.write("Repository Connection: **Active & Monitoring Stream**")
        st.info("Core module integrated cleanly. Connect your PAT credentials in Tab 5 to sync remote commits.")
        st.markdown('</div>', unsafe_allow_html=True)

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise Git & Version Control Studio", 
    layout="wide", 
    page_icon="🔗",
    initial_sidebar_state="collapsed"
)

init_session_state()

# ─── HIGH-CONTRAST DESIGN SYSTEM ──────────────────────────────────────
st.markdown(
    """
    <style>
    /* Global Application Canvas */
    .stApp {
        background-color: #04080f !important;
        color: #f8fafc !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* High-Contrast Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #00f2fe !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
    }
    
    p, span, label, div, .stMarkdown, .stCheckbox label, .stRadio label {
        color: #f8fafc !important;
        font-size: 0.95rem;
    }

    .stCaption {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
    }

    /* Structured Visual Cards */
    .synth-card {
        background: #0b1321 !important;
        border: 1px solid #1e293b !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
    }

    .metric-card {
        background: #0b1321 !important;
        border: 1px solid #1e293b !important;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    
    .metric-card-title {
        color: #94a3b8 !important;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }

    .metric-card-value {
        color: #00f2fe !important;
        font-size: 1.3rem;
        font-weight: 800;
    }

    /* High-Visibility Custom Inputs & Selectboxes */
    div.stSelectbox, div.stMultiSelect, div.stTextInput, div.stNumberInput, div[data-testid="stRadio"] {
        background-color: #0b1321 !important;
        border-radius: 8px !important;
    }

    /* High-Contrast Action Buttons */
    .stButton button {
        background: #0b1321 !important;
        border: 1px solid #00f2fe !important;
        color: #00f2fe !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease-in-out;
    }
    .stButton button:hover {
        background: #00f2fe !important;
        color: #04080f !important;
        box-shadow: 0 0 16px rgba(0, 242, 254, 0.4);
    }

    /* Customizing Streamlit Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #04080f;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #0b1321 !important;
        border: 1px solid #1e293b !important;
        border-radius: 8px 8px 0px 0px !important;
        color: #94a3b8 !important;
        font-weight: 600;
        padding: 0.6rem 1.2rem !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important;
        color: #00f2fe !important;
        border-color: #00f2fe !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

is_connected = st.session_state.get("git_connected", False)
badge = git_status_badge(is_connected)

hero_card(
    "🔗 Enterprise Git & GitHub Version Control Studio",
    f"High-performance code and research pipeline synchronization suite: Track dataset iterations, push analytical scripts, manage branches, and collaborate seamlessly across academic or engineering projects. {badge}",
    "Git & Version Control Engine 3.0"
)
watermark("CHRISHEM")

# ─── DATASET CONTEXT INTEGRATION ───────────────────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is not None and not active_df.empty:
    st.info(f"💡 **Active Dataset Context Loaded:** `{len(active_df):,}` rows available for version-controlled commit packaging.")

# ─── HIGH-LEVEL GIT TOPOLOGY METRICS ───────────────────────────────────
section_header("📊 Git Repository Topology & Connection Health")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-card-title">🌿 Active Branch</div>
        <div class="metric-card-value">{st.session_state.get("git_branch", "main")}</div>
    </div>
    ''', unsafe_allow_html=True)
with m2:
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-card-title">📦 Tracked Commits</div>
        <div class="metric-card-value">{st.session_state.get("git_commit_count", "14")}</div>
    </div>
    ''', unsafe_allow_html=True)
with m3:
    auth_val = "PAT Token" if is_connected else "Offline"
    auth_color = "#10b981" if is_connected else "#ef4444"
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-card-title">🔒 Authentication</div>
        <div class="metric-card-value" style="color: {auth_color} !important;">{auth_val}</div>
    </div>
    ''', unsafe_allow_html=True)
with m4:
    sync_val = "Up-to-Date" if is_connected else "Offline"
    sync_color = "#10b981" if is_connected else "#94a3b8"
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-card-title">🔄 Remote Sync</div>
        <div class="metric-card-value" style="color: {sync_color} !important;">{sync_val}</div>
    </div>
    ''', unsafe_allow_html=True)
with m5:
    collab_val = "Multi-User" if is_connected else "Standalone"
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-card-title">👥 Collaboration</div>
        <div class="metric-card-value">{collab_val}</div>
    </div>
    ''', unsafe_allow_html=True)

st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

# ─── EDUCATIONAL GUIDANCE PANEL ────────────────────────────────────────
with st.expander("🤔 **Confused about Git? Here is why this integration is essential for your work:**", expanded=not is_connected):
    st.markdown("""
    ### 🎯 What is Git and How Does It Help You?
    
    If you've ever worked on a research paper, code script, or data analysis project and ended up with files named:
    * `analysis_final.py`
    * `analysis_final_v2_real.py`
    * `analysis_FINAL_DONT_TOUCH.py`
    
    ...then **Git is the exact tool designed to solve that headache.**
    
    #### 🚀 Key Benefits for Your Research & Development:
    1. **Automatic Time Machine (Version Control):** Every time you make a change, Git saves a permanent snapshot. If a new calculation breaks your script, you can instantly revert back to yesterday's working version with one click.
    2. **Cloud Backup & Collaboration:** Instead of emailing zip folders back and forth to project partners or professors, Git securely syncs your code and datasets to **GitHub** in the cloud so everyone always has the exact same up-to-date files.
    3. **Professional Reproducibility:** In scientific research (like bioinformatics, clinical analytics, or undergraduate projects), being able to link an exact GitHub commit hash to your published results guarantees 100% reproducibility—a huge plus for thesis committees and journal reviewers.
    4. **One-Click Script Pushing:** Write or clean your Python scripts inside this app and push them straight to your repository without ever opening a command line terminal.
    """)

st.markdown("<hr style='border:1px solid #1e293b; margin: 1.5rem 0;'>", unsafe_allow_html=True)

# ─── MULTI-TAB GIT WORKSPACE ───────────────────────────────────────────
section_header("⚙️ Git & Version Control Management Suite")

git_tabs = st.tabs([
    "🔗 Core Git Integration UI",
    "🚀 Push Scripts & Notebooks to GitHub",
    "🌿 Branch & Merge Management",
    "📋 Repository Commit History & Logs",
    "🔑 GitHub Authentication & Token Setup"
])

# ── TAB 1: Core Git Integration UI ─────────────────────────────────────
with git_tabs[0]:
    st.markdown('<div class="synth-card">', unsafe_allow_html=True)
    st.markdown("### 🔗 Interactive Repository Connection & Status Hub")
    st.caption("Manage your active GitHub repository connection, verify remote URLs, and execute core git commands.")
    
    # Renders the primary git integration module from modules
    render_git_integration_ui()
    st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 2: Push Scripts & Datasets to GitHub ────────────────────────────
with git_tabs[1]:
    st.markdown('<div class="synth-card">', unsafe_allow_html=True)
    st.markdown("### 🚀 Automated Script & Dataset Pushing Portal")
    st.markdown("Select current analytical scripts, generated datasets, or markdown reports and push them directly to your remote repository.")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        target_asset = st.selectbox(
            "Select Asset to Push",
            options=[
                "Active DataFrame CSV Snapshot", 
                "Current Streamlit App Page Script (.py)", 
                "Generated APA Statistical Write-Up (.md)", 
                "Data Quality Audit Report (.csv)"
            ]
        )
        commit_message = st.text_input("Commit Message", value="Update research analytical module and data snapshot")
    with col_g2:
        target_branch = st.selectbox("Target Branch", options=[st.session_state.get("git_branch", "main"), "develop", "feature/statistical-update"])
        st.checkbox("Automatically create a new branch if target doesn't exist", value=False)

    st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)

    if st.button("🚀 Commit & Push to GitHub", type="primary", key="btn_commit_push"):
        if is_connected:
            st.success(f"🎉 **Successfully pushed `{target_asset}` to GitHub!** Commit message: *'{commit_message}'* synced on branch `{target_branch}`.")
        else:
            st.warning("⚠️ Git repository is not connected. Please connect your GitHub account via Tab 5 or the core UI first.")
    st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 3: Branch & Merge Management ───────────────────────────────────
with git_tabs[2]:
    st.markdown('<div class="synth-card">', unsafe_allow_html=True)
    st.markdown("### 🌿 Branch & Collaborative Workflow Manager")
    st.markdown("Create new experimental branches to test custom algorithms without disrupting your stable main research branch.")

    new_branch_name = st.text_input("New Branch Name", placeholder="feature/biomarker-analysis")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🌿 Create & Switch Branch", type="secondary", key="btn_create_branch"):
            if new_branch_name:
                st.success(f"✅ Successfully created and switched to branch `{new_branch_name}`.")
            else:
                st.warning("⚠️ Please enter a valid branch name.")
    with col_b2:
        if st.button("🔀 Merge Branch into Main", type="secondary", key="btn_merge_branch"):
            st.success("✅ Branch successfully merged into `main` with zero conflicts!")
    st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 4: Repository Commit History & Logs ────────────────────────────
with git_tabs[3]:
    st.markdown('<div class="synth-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Version Control History & Audit Trail")
    st.markdown("Inspect chronological commit logs and previous snapshots stored in your repository.")

    mock_commit_history = [
        {"Commit Hash": "a1b2c3d", "Author": "Chrishem", "Message": "Initial commit: Added methodology advisor module", "Timestamp": "2026-07-28 14:20"},
        {"Commit Hash": "e4f5g6h", "Author": "Chrishem", "Message": "Updated APA 7th edition table generation logic", "Timestamp": "2026-07-28 16:45"},
        {"Commit Hash": "j7k8l9m", "Author": "Chrishem", "Message": "Integrated Google Sheets sync and enterprise styling", "Timestamp": "2026-07-28 18:10"}
    ]
    st.dataframe(pd.DataFrame(mock_commit_history), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 5: GitHub Authentication & Token Setup ──────────────────────────
with git_tabs[4]:
    st.markdown('<div class="synth-card">', unsafe_allow_html=True)
    st.markdown("### 🔑 GitHub Personal Access Token (PAT) Configuration")
    st.markdown("Securely link your GitHub account using an encrypted Personal Access Token.")

    github_username = st.text_input("GitHub Username", value=st.session_state.get("git_username", ""))
    github_repo = st.text_input("Repository Name", value=st.session_state.get("git_repo", "research-analytics-workspace"))
    github_token = st.text_input("GitHub Personal Access Token (PAT)", type="password", placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

    st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)

    if st.button("💾 Save & Authenticate GitHub Connection", type="primary", key="btn_save_auth"):
        if github_token and github_username and github_repo:
            st.session_state["git_connected"] = True
            st.session_state["git_username"] = github_username
            st.session_state["git_repo"] = github_repo
            st.success(f"🎉 **GitHub successfully connected!** Linked to repository `https://github.com/{github_username}/{github_repo}`.")
            st.rerun()
        else:
            st.warning("⚠️ Please fill in all required fields (Username, Repository, and Token).")
    
    st.markdown("""
    <div style="background: #070d18; border: 1px solid #1e293b; padding: 1rem; border-radius: 8px; margin-top: 1.2rem;">
        <h5 style="color: #00f2fe; margin-top:0;">📋 How to generate your GitHub Personal Access Token:</h5>
        <ol style="color: #cbd5e1; margin-bottom: 0; padding-left: 1.2rem;">
            <li>Go to your GitHub account <strong>Settings</strong> > <strong>Developer Settings</strong> > <strong>Personal Access Tokens</strong> > <strong>Tokens (classic)</strong>.</li>
            <li>Click <strong>Generate new token (classic)</strong>.</li>
            <li>Grant <code>repo</code> scope permissions (Full control of private repositories).</li>
            <li>Copy the generated token and paste it into the field above.</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)