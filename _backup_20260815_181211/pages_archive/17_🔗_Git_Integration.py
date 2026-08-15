"""
══════════════════════════════════════════════════════════════════════════════
ENTERPRISE GIT & VERSION CONTROL STUDIO [v4.0 - INTELLIGENT PROBLEM SOLVER]
High-performance version control pipeline featuring real repository initialization,
live status scanning, automated script commits, staging diff inspection, and 
true local/remote synchronization.
Designed for: Chrishem Studio Engine
══════════════════════════════════════════════════════════════════════════════
"""

import sys
import os
import subprocess
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
            f"<h3 style='color:#00f2fe !important; margin-top:1.6rem; margin-bottom:0.4rem; font-weight:800; letter-spacing:-0.02em;'>{text}</h3>", 
            unsafe_allow_html=True
        )
        if desc:
            st.caption(desc)

    def git_status_badge(is_connected=False):
        if is_connected:
            return "<span style='background: rgba(16, 185, 129, 0.15); color: #10b981; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; border: 1px solid #10b981;'>🟢 Live Repo Connected</span>"
        return "<span style='background: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; border: 1px solid #ef4444;'>🔴 Local Workspace Only</span>"

    def hero_card(title, subtitle, badge_text=""):
        st.markdown(f"""
        <div style="padding: 1.75rem; background: linear-gradient(135deg, rgba(0, 242, 254, 0.1) 0%, rgba(11, 19, 33, 0.98) 100%); border-radius: 14px; border: 1px solid rgba(0, 242, 254, 0.3); margin-bottom: 1.5rem; box-shadow: 0 8px 32px rgba(0,0,0,0.4);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.75rem;">
                <h1 style="color: #00f2fe !important; font-size: 2.15rem; margin: 0; font-weight: 800; letter-spacing: -0.03em;">{title}</h1>
                <span style="background: rgba(0, 242, 254, 0.15); color: #00f2fe; padding: 0.35rem 0.9rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; border: 1px solid #00f2fe;">{badge_text}</span>
            </div>
            <p style="color: #cbd5e1 !important; font-size: 1rem; margin: 0; line-height: 1.5;">{subtitle}</p>
        </div>
        """, unsafe_allow_html=True)

    def render_git_integration_ui():
        st.markdown('<div class="synth-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='color:#00f2fe;'>🔍 Live Subprocess Git Engine Status</h4>", unsafe_allow_html=True)
        st.write("Executing workspace scans via local git runtime...")
        st.markdown('</div>', unsafe_allow_html=True)

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise Git & Version Control Studio", 
    layout="wide", 
    page_icon="⚡",
    initial_sidebar_state="collapsed"
)

init_session_state()

# ─── PREMIUM TYPOGRAPHY & HIGH-CONTRAST DESIGN SYSTEM ──────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #070a12 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    .stApp {
        background-color: #030712 !important;
        color: #f8fafc !important;
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    code, pre, .stCodeBlock {
        font-family: 'JetBrains Mono', monospace !important;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #00f2fe !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
    }
    
    p, span, label, div, .stMarkdown, .stCheckbox label, .stRadio label {
        color: #e2e8f0 !important;
        font-size: 0.95rem;
        line-height: 1.5;
    }

    .stCaption {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
    }

    .synth-card {
        background: #0b132b !important;
        border: 1px solid #1e293b !important;
        border-radius: 14px;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }

    .metric-card {
        background: #0b132b !important;
        border: 1px solid #1e293b !important;
        border-radius: 12px;
        padding: 1.15rem;
        text-align: center;
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        border-color: #00f2fe;
        transform: translateY(-2px);
    }
    
    .metric-card-title {
        color: #94a3b8 !important;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.4rem;
    }

    .metric-card-value {
        color: #00f2fe !important;
        font-size: 1.35rem;
        font-weight: 800;
    }

    div.stSelectbox, div.stMultiSelect, div.stTextInput, div.stNumberInput, div[data-testid="stRadio"] {
        background-color: #0b132b !important;
        border-radius: 8px !important;
    }

    .stButton button {
        background: #0b132b !important;
        border: 1px solid #00f2fe !important;
        color: #00f2fe !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        padding: 0.5rem 1rem;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stButton button:hover {
        background: #00f2fe !important;
        color: #030712 !important;
        box-shadow: 0 0 20px rgba(0, 242, 254, 0.5);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #030712;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #0b132b !important;
        border: 1px solid #1e293b !important;
        border-radius: 10px 10px 0px 0px !important;
        color: #94a3b8 !important;
        font-weight: 600;
        padding: 0.7rem 1.4rem !important;
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

# ─── REAL GIT SUBPROCESS RUNTIME ENGINE ──────────────────────────────
def run_git_command(cmd_list):
    """Executes a real local git command safely via subprocess and returns output/error."""
    try:
        result = subprocess.run(
            cmd_list,
            cwd=str(root_dir),
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()
    except Exception as ex:
        return False, str(ex)

# Inspect live local repository state
is_git_repo, _ = run_git_command(["git", "rev-parse", "--is-inside-work-tree"])
is_connected = is_git_repo

# Fetch branch if repo exists
current_branch = "main"
commit_count = "0"
if is_git_repo:
    _, branch_out = run_git_command(["git", "branch", "--show-current"])
    if branch_out:
        current_branch = branch_out
    _, count_out = run_git_command(["git", "rev-list", "--count", "HEAD"])
    if count_out:
        commit_count = count_out

badge = git_status_badge(is_connected)

hero_card(
    "⚡ Enterprise Git & GitHub Version Control Engine",
    f"High-performance local repository intelligence & synchronization suite: Perform real-time file staging, inspect diffs, execute atomic commits, manage branches, and push directly to GitHub remotes. {badge}",
    "Intelligent Version Control Hub 4.0"
)
watermark("CHRISHEM")

# ─── DATASET & ACTIVE SESSION CONTEXT ─────────────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is not None and not active_df.empty:
    st.info(f"📊 **Active Session Dataset Detected:** `{len(active_df):,}` rows available in memory to snapshot or export into your repository.")

# ─── TOPOLOGY & HEALTH METRICS ────────────────────────────────────────
section_header("Repository Topology & Live System Diagnostics")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-card-title">Active Branch</div>
        <div class="metric-card-value">{current_branch}</div>
    </div>
    ''', unsafe_allow_html=True)
with m2:
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-card-title">Total Commits</div>
        <div class="metric-card-value">{commit_count}</div>
    </div>
    ''', unsafe_allow_html=True)
with m3:
    repo_status_text = "Initialized" if is_git_repo else "Not Initialized"
    repo_color = "#10b981" if is_git_repo else "#ef4444"
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-card-title">Git Runtime</div>
        <div class="metric-card-value" style="color: {repo_color} !important;">{repo_status_text}</div>
    </div>
    ''', unsafe_allow_html=True)
with m4:
    sync_status = "Local Active" if is_git_repo else "Offline"
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-card-title">Sync Protocol</div>
        <div class="metric-card-value" style="color: #38bdf8 !important;">{sync_status}</div>
    </div>
    ''', unsafe_allow_html=True)
with m5:
    st.markdown(f'''
    <div class="metric-card">
        <div class="metric-card-title">Workspace Root</div>
        <div class="metric-card-value" style="font-size: 0.95rem; padding-top: 0.2rem;">{root_dir.name}</div>
    </div>
    ''', unsafe_allow_html=True)

st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

# ─── MULTI-TAB INTELLIGENT WORKSPACE ───────────────────────────────────
section_header("Version Control & Repository Operations Suite")

git_tabs = st.tabs([
    "🔍 Live Repository Status & Diffs",
    "📝 Staging & Intelligent Commit Studio",
    "🌿 Branch & Merge Management",
    "📜 Chronological Commit History",
    "⚡ Initialize & Remote Setup"
])

# ── TAB 1: Live Repository Status & Diffs ──────────────────────────────
with git_tabs[0]:
    st.markdown('<div class="synth-card">', unsafe_allow_html=True)
    st.markdown("### 🔍 Live Workspace Status & File Changes")
    st.caption("Inspect untracked files, modified scripts, and staging changes directly from your local project folder.")

    if is_git_repo:
        success, status_out = run_git_command(["git", "status", "--short"])
        if success:
            if status_out:
                st.warning("⚠️ Uncommitted changes detected in your workspace:")
                st.code(status_out, language="text")
            else:
                st.success("✨ Working tree clean! All files are committed and synchronized.")
        
        st.markdown("#### Live File Diff Inspector")
        success_diff, diff_out = run_git_command(["git", "diff"])
        if success_diff and diff_out:
            st.code(diff_out, language="diff")
        else:
            st.info("No active line diffs found in modified files.")
    else:
        st.error("⚠️ No Git repository initialized in this environment. Go to Tab 5 to initialize a repository.")

    st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 2: Staging & Intelligent Commit Studio ──────────────────────────
with git_tabs[1]:
    st.markdown('<div class="synth-card">', unsafe_allow_html=True)
    st.markdown("### 📝 Intelligent Commit & Snapshot Studio")
    st.markdown("Stage project assets, write descriptive commit messages, and snapshot your analysis securely.")

    if is_git_repo:
        success, status_out = run_git_command(["git", "status", "--porcelain"])
        untracked_files = [line[3:] for line in status_out.splitlines()] if status_out else []

        selected_files = st.multiselect(
            "Select Files to Stage & Commit", 
            options=untracked_files if untracked_files else ["All Workspace Changes (.)"],
            default=untracked_files if untracked_files else []
        )
        
        commit_msg = st.text_input("Commit Message", placeholder="feat: update analytical pipeline and session metrics")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("📦 Stage & Commit Changes", type="primary", use_container_width=True):
                if commit_msg:
                    if selected_files and "All Workspace Changes (.)" not in selected_files:
                        for f in selected_files:
                            run_git_command(["git", "add", f])
                    else:
                        run_git_command(["git", "add", "."])
                    
                    success_commit, commit_out = run_git_command(["git", "commit", "-m", commit_msg])
                    if success_commit:
                        st.success("✅ Changes successfully committed to local repository!")
                        st.code(commit_out)
                        st.rerun()
                    else:
                        st.error(f"Commit failed: {commit_out}")
                else:
                    st.warning("Please provide a valid commit message.")
        with col_c2:
            if st.button("🚀 Push to Remote Origin", use_container_width=True):
                success_push, push_out = run_git_command(["git", "push", "origin", current_branch])
                if success_push:
                    st.success("Successfully pushed commits to remote repository!")
                else:
                    st.error(f"Push failed (Check remote configuration): {push_out}")
    else:
        st.warning("⚠️ Initialize a Git repository first in Tab 5.")

    st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 3: Branch & Merge Management ───────────────────────────────────
with git_tabs[2]:
    st.markdown('<div class="synth-card">', unsafe_allow_html=True)
    st.markdown("### 🌿 Branch & Collaborative Workflow Manager")
    st.markdown("Isolate experimental features or research revisions into dedicated branches without touching your stable code.")

    if is_git_repo:
        success, branches_out = run_git_command(["git", "branch"])
        if success:
            st.markdown(f"**Existing Branches:**\n```text\n{branches_out}\n```")

        new_branch_input = st.text_input("New Branch Name", placeholder="feature/bioinformatics-model")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("🌿 Create & Switch Branch", use_container_width=True):
                if new_branch_input:
                    ok, err = run_git_command(["git", "checkout", "-b", new_branch_input])
                    if ok:
                        st.success(f"Successfully created and switched to branch `{new_branch_input}`!")
                        st.rerun()
                    else:
                        st.error(f"Error: {err}")
                else:
                    st.warning("Enter a valid branch name.")
        with col_b2:
            target_merge = st.text_input("Branch to Merge Into Current", placeholder="main")
            if st.button("🔀 Merge Branch", use_container_width=True):
                ok, err = run_git_command(["git", "merge", target_merge])
                if ok:
                    st.success(f"Successfully merged `{target_merge}` into `{current_branch}`!")
                else:
                    st.error(f"Merge conflict or error: {err}")
    else:
        st.warning("⚠️ Git repository not initialized.")

    st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 4: Chronological Commit History ────────────────────────────────
with git_tabs[3]:
    st.markdown('<div class="synth-card">', unsafe_allow_html=True)
    st.markdown("### 📜 Chronological Commit History & Audit Trail")
    st.markdown("Inspect past snapshots, author metadata, and commit hashes for reproducibility.")

    if is_git_repo:
        success, log_out = run_git_command(["git", "log", "--oneline", "-n", "15"])
        if success and log_out:
            st.code(log_out, language="text")
        else:
            st.info("No commit history found yet on this branch.")
    else:
        st.warning("⚠️ Git repository not initialized.")

    st.markdown('</div>', unsafe_allow_html=True)

# ── TAB 5: Initialize & Remote Setup ───────────────────────────────────
with git_tabs[4]:
    st.markdown('<div class="synth-card">', unsafe_allow_html=True)
    st.markdown("### ⚡ Repository Initialization & Remote Configuration")
    st.markdown("Initialize your workspace as a Git repository or link it to a remote GitHub repository URL.")

    col_i1, col_i2 = st.columns(2)
    with col_i1:
        st.markdown("#### Initialize Local Git")
        if st.button("⚙️ Run `git init` on Workspace", use_container_width=True):
            ok, err = run_git_command(["git", "init"])
            if ok:
                st.success("Successfully initialized local Git repository!")
                st.rerun()
            else:
                st.error(f"Initialization error: {err}")

    with col_i2:
        st.markdown("#### Connect Remote Origin")
        remote_url = st.text_input("Remote Repository URL", placeholder="https://github.com/username/repo.git")
        if st.button("🔗 Set Remote Origin", use_container_width=True):
            if remote_url:
                run_git_command(["git", "remote", "remove", "origin"])
                ok, err = run_git_command(["git", "remote", "add", "origin", remote_url])
                if ok:
                    st.success(f"Successfully linked remote origin: `{remote_url}`!")
                else:
                    st.error(f"Error setting remote: {err}")
            else:
                st.warning("Please provide a valid remote URL.")

    st.markdown('</div>', unsafe_allow_html=True)