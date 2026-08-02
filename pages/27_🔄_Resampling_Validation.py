"""
Advanced Resampling & Validation Page — Bootstrap, permutation tests, cross-validation, Monte Carlo.
"""
import streamlit as st

st.set_page_config(page_title="Resampling & Validation", page_icon="🔄", layout="wide")

from modules.page_setup import require_dependency
from modules.resampling_engine import render_resampling_ui

require_dependency("scipy", "⚠️ scipy required. Install with: `pip install scipy`")

render_resampling_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Bootstrap methods make no distributional assumptions. Use permutation tests for non-parametric group comparisons.")
