st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""
Bayesian Analysis Page — Bayesian t-tests, ANOVA, regression with Bayes factors.
"""
import streamlit as st

st.set_page_config(page_title="Bayesian Analysis", page_icon="🧠", layout="wide")

from modules.bayesian_engine import render_bayesian_analysis_ui

try:
    import pymc as pm
    HAS_PYMC = True
except ImportError:
    HAS_PYMC = False

if not HAS_PYMC:
    st.warning("⚠️ PyMC not installed. Bayesian MCMC models will use pingouin/scipy fallback. Install with: `pip install pymc arviz`")

render_bayesian_analysis_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Bayesian methods provide intuitive probability statements about parameters. BF10 > 3 indicates substantial evidence for H1.")
