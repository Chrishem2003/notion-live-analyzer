"""
Meta-Analysis Page — Combine effect sizes across studies, assess heterogeneity,
detect publication bias, and generate publication-ready forest/funnel plots.
"""

import streamlit as st

st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
import pandas as pd

# Must be first Streamlit command
st.set_page_config(
    page_title="Meta-Analysis Engine",
    page_icon="📊",
    layout="wide",
)

from modules.meta_analysis import render_meta_analysis_ui

# ─── Check dependencies ──────────────────────────────────────────────
try:
    from scipy import stats
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

if not HAS_DEPS:
    st.error(
        "⚠️ Required dependencies not installed.\n\n"
        "Please go to **⚙️ Settings → Dependency Manager** and install missing packages, "
        "or run: `pip install scipy statsmodels`"
    )
    st.stop()

# ─── Render the meta-analysis UI ─────────────────────────────────────
render_meta_analysis_ui()

# ─── Navigation hint ─────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Tip:** Add at least 2 studies to run a meta-analysis. "
    "The forest plot and funnel plot will auto-generate. "
    "For publication bias detection, you need ≥3 studies."
)

