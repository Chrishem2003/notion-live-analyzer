"""
Research Quality & Reproducibility Page — p-Hacking detection, QRP detection, reproducibility check.
"""

import streamlit as st
st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>", unsafe_allow_html=True)
st.set_page_config(page_title="Research Quality", page_icon="✅", layout="wide")

from modules.research_quality import render_research_quality_ui

try:
    import numpy as np
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

if not HAS_DEPS:
    st.error("⚠️ numpy required.")
    st.stop()

df = st.session_state.get("active_df")
statistical_results = st.session_state.get("statistical_results", [])

render_research_quality_ui(statistical_results, df)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Run statistical analyses on the 🔬 Statistical Tests page first, then check for p-hacking and QRPs here.")
