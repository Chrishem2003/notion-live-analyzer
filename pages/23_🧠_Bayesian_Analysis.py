"""
Bayesian Analysis Page — Bayesian t-tests, ANOVA, regression with Bayes factors.
"""
import streamlit as st

st.set_page_config(page_title="Bayesian Analysis", page_icon="🧠", layout="wide")

from modules.page_setup import require_dependency
from modules.bayesian_engine import render_bayesian_analysis_ui

require_dependency("pymc", "⚠️ PyMC not installed. Bayesian MCMC models will use pingouin/scipy fallback. Install with: `pip install pymc arviz`", stop=False)

render_bayesian_analysis_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Bayesian methods provide intuitive probability statements about parameters. BF10 > 3 indicates substantial evidence for H1.")
