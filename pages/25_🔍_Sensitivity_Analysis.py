st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""
Sensitivity & Robustness Analysis Page — Influence diagnostics, specification curve, multiverse analysis.
"""
import streamlit as st

st.set_page_config(page_title="Sensitivity Analysis", page_icon="🔍", layout="wide")

from modules.sensitivity_engine import render_sensitivity_analysis_ui

try:
    from scipy import stats
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

if not HAS_DEPS:
    st.error("⚠️ scipy required. Install with: `pip install scipy statsmodels`")
    st.stop()

render_sensitivity_analysis_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Sensitivity analysis tests how robust your findings are to different analytical choices. Always run before finalizing results.")
