"""
📑 APA Outputs Page — Advanced Enterprise APA 7th Edition Statistical Reporting, Academic Write-Up Studio, & Manuscript Formatter.
"""
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Enterprise APA 7th Edition Studio", 
    layout="wide", 
    page_icon="📑"
)

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header
from modules.apa_formatter import render_apa_outputs_page, render_apa_quick_format_ui

init_session_state()
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

hero_card(
    "📑 Enterprise APA 7th Edition Publication Studio", 
    "High-precision academic reporting engine: Automated statistical write-ups, APA 7th edition compliance checking, effect size formatting, table generation, and manuscript export tools.", 
    "APA Style & Academic Publishing Engine 3.0"
)
watermark("CHRISHEM")

# ─── Dataset Context Integration (Optional) ────────────────────────────
active_df = st.session_state.get("active_df")
if active_df is None or active_df.empty:
    active_df = st.session_state.get("notion_df")

if active_df is not None and not active_df.empty:
    st.info(f"💡 **Active Dataset Context Loaded:** `{len(active_df):,}` rows available for automated APA statistical result compilation.")

# Collect results from session state
statistical_results = st.session_state.get("statistical_results", [])

# ─── High-Level APA Reporting Topology Metrics ─────────────────────────
section_header("📊 APA Compliance & Result Stream Status")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("📋 Active Stored Results", len(statistical_results))
with m2:
    st.metric("📐 Edition Standard", "APA 7th", help="American Psychological Association latest guidelines")
with m3:
    st.metric("🔬 Test Categories", "Parametric & Non-Parametric")
with m4:
    st.metric("📊 Effect Sizes", "Cohen's d, Eta², Cramer's V")
with m5:
    st.metric("💾 Export Formats", "Word, LaTeX, Markdown")

st.markdown("---")

# ─── Multi-Tab APA Reporting Workspace ─────────────────────────────────
section_header("⚙️ Academic Manuscript & APA Generation Suite")

apa_tabs = st.tabs([
    "📄 Formatted Statistical Results",
    "🔧 Quick APA Result Formatter",
    "📊 APA Table Generator (Table 1 / 7th Edition)",
    "📑 Complete Manuscript Write-Up Generator"
])

# ── TAB 1: Formatted Results ───────────────────────────────────────────
with apa_tabs[0]:
    st.markdown("### 📄 Session Statistical Results Repository")
    st.caption("Review and export all automatically captured statistical outputs formatted strictly to APA 7th edition standards.")
    
    render_apa_outputs_page(statistical_results if statistical_results else None)

# ── TAB 2: Quick APA Formatter ──────────────────────────────────────────
with apa_tabs[1]:
    st.markdown("### 🔧 Instant APA Statistical Sentence Builder")
    st.markdown("Interactively input test statistics ($t$, $F$, $r$, $\chi^2$) to generate flawless APA-compliant reporting sentences.")
    
    render_apa_quick_format_ui()

# ── TAB 3: APA Table Generator ──────────────────────────────────────────