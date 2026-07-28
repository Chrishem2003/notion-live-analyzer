"""
📑 World-Class Multi-Paper Meta-Analysis Matrix Synthesizer
Enterprise-grade systematic review and evidence synthesis engine featuring automated effect-size extraction,
heterogeneity modeling ($I^2$, Cochran's Q), publication bias Egger's regression testing, and forest plot generation pipelines.
"""
import streamlit as st

st.set_page_config(
    page_title="Multi-Paper Meta-Analysis Matrix Synthesizer",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. META-ANALYSIS SESSION STATE & CONFIGURATION
# ==========================================
if "meta_matrix_active" not in st.session_state:
    st.session_state["meta_matrix_active"] = False
if "meta_model_type" not in st.session_state:
    st.session_state["meta_model_type"] = "Random-Effects Model (DerSimonian-Laird)"

from modules.meta_analysis_matrix import (
    render_meta_analysis_matrix_ui,
    init_meta_matrix_state,
    load_meta_matrix_stylesheet
)

# Initialize secure application state and responsive styling pipelines
init_meta_matrix_state()
load_meta_matrix_stylesheet(is_dark=st.session_state.get("theme", "light") == "dark")

# ==========================================
# 2. SYNTHESIS CONTROL HUD & PARAMETERS
# ==========================================

with st.sidebar:
    st.markdown("### ⚙️ Statistical Synthesis Model")
    model_type = st.selectbox(
        "Pooling Architecture",
        [
            "Random-Effects Model (DerSimonian-Laird)",
            "Fixed-Effect Model (Mantel-Haenszel / Peto)",
            "Bayesian Hierarchical Meta-Analysis",
            "Multivariate Meta-Regression"
        ],
        key="meta_model_type_select"
    )
    st.session_state["meta_model_type"] = model_type

    st.markdown("---")
    st.markdown("### 📊 Effect Size & Metric Metrics")
    effect_metric = st.selectbox(
        "Primary Effect Metric",
        ["Odds Ratio (OR)", "Relative Risk (RR)", "Risk Difference (RD)", "Standardized Mean Difference (SMD)", "Pearson's Correlation (r)"],
        key="meta_effect_metric"
    )
    confidence_level = st.slider("Confidence Interval (%)", 90, 99, 95, 1, key="meta_confidence_level")

    st.markdown("---")
    st.markdown("### 🛡️ Bias Detection & Heterogeneity")
    st.toggle("Egger's Test for Publication Bias", value=True, key="meta_eggers_toggle")
    st.toggle("Fail-Safe N Calculation (Rosenthal)", value=True, key="meta_failsafe_toggle")
    st.toggle("Leave-One-Out Sensitivity Analysis", value=True, key="meta_sensitivity_toggle")
    st.toggle("Trim-and-Fill Imputation", value=True, key="meta_trimfill_toggle")

# ==========================================
# 3. MAIN META-ANALYSIS MATRIX WORKSPACE
# ==========================================

# Render high-performance meta-analysis matrix synthesis interface with parameter binding
render_meta_analysis_matrix_ui(
    model_type=model_type,
    effect_metric=effect_metric,
    confidence_level=confidence_level
)