"""
Advanced Resampling & Validation Page — Bootstrap, permutation tests, cross-validation, Monte Carlo.
"""
import streamlit as st

st.set_page_config(page_title="Resampling & Validation", page_icon="🔄", layout="wide")

from modules.resampling_engine import render_resampling_ui

try:
    from scipy import stats
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

if not HAS_DEPS:
    st.error("⚠️ scipy required. Install with: `pip install scipy`")
    st.stop()

render_resampling_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Bootstrap methods make no distributional assumptions. Use permutation tests for non-parametric group comparisons.")
