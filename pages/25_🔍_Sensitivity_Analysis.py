"""
Sensitivity & Robustness Analysis Page — Influence diagnostics, specification curve, multiverse analysis.
"""
import streamlit as st

st.set_page_config(page_title="Sensitivity Analysis", page_icon="🔍", layout="wide")

from modules.page_setup import require_dependency
from modules.sensitivity_engine import render_sensitivity_analysis_ui

require_dependency("scipy", "⚠️ scipy required. Install with: `pip install scipy statsmodels`")

render_sensitivity_analysis_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Sensitivity analysis tests how robust your findings are to different analytical choices. Always run before finalizing results.")
