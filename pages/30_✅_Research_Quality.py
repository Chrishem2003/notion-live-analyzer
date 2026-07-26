"""
Research Quality & Reproducibility Page — p-Hacking detection, QRP detection, reproducibility check.
"""
import streamlit as st

st.set_page_config(page_title="Research Quality", page_icon="✅", layout="wide")

from modules.page_setup import require_dependency
from modules.research_quality import render_research_quality_ui

require_dependency("numpy", "⚠️ numpy required.")

df = st.session_state.get("active_df")
statistical_results = st.session_state.get("statistical_results", [])

render_research_quality_ui(statistical_results, df)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Run statistical analyses on the 🔬 Statistical Tests page first, then check for p-hacking and QRPs here.")
