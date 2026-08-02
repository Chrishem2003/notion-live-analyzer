"""
Causal Analysis Page — Propensity score matching, DiD, IV regression, DAGs.
"""
import streamlit as st

st.set_page_config(page_title="Causal Analysis", page_icon="🔬", layout="wide")

from modules.page_setup import require_dependency
from modules.causal_inference import render_causal_inference_ui

require_dependency("causalml.inference.tree", "⚠️ causalml not fully installed. Propensity score matching and CATE estimation will use scikit-learn fallback. Install with: `pip install causalml`", stop=False)

render_causal_inference_ui()

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Use causal inference to estimate treatment effects from observational data. PSM, DiD, IV, and DAG tools available.")
