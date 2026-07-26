"""
Meta-Analysis Page — Combine effect sizes across studies, assess heterogeneity,
detect publication bias, and generate publication-ready forest/funnel plots.
"""
import streamlit as st
import pandas as pd

# Must be first Streamlit command
st.set_page_config(
    page_title="Meta-Analysis Engine",
    page_icon="📊",
    layout="wide",
)

from modules.page_setup import require_dependency
from modules.meta_analysis import render_meta_analysis_ui

# ─── Check dependencies ──────────────────────────────────────────────
require_dependency(
    "scipy",
    "⚠️ Required dependencies not installed.\n\n"
    "Please go to **⚙️ Settings → Dependency Manager** and install missing packages, "
    "or run: `pip install scipy statsmodels`",
)

# ─── Render the meta-analysis UI ─────────────────────────────────────
render_meta_analysis_ui()

# ─── Navigation hint ─────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Tip:** Add at least 2 studies to run a meta-analysis. "
    "The forest plot and funnel plot will auto-generate. "
    "For publication bias detection, you need ≥3 studies."
)

