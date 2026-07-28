"""
🔬 Advanced Active Bias & Methodological Flaw Detector
Comprehensive research audit engine featuring real-time statistical power analysis,
confounding variable stress-testing, Bayesian bias correction, and automated remediation pipelines.
"""
import streamlit as st

st.set_page_config(
    page_title="Active Bias & Methodological Flaw Detector",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

from modules.methodology_auditor import (
    render_methodology_auditor_ui,
    init_auditor_session_state,
    load_auditor_stylesheet
)

# Initialize session configuration & secure styling pipelines
init_auditor_session_state()
load_auditor_stylesheet(is_dark=st.session_state.get("theme", "light") == "dark")

# ==========================================
# 1. ADVANCED ENGINE STATE & CONFIGURATION HUD
# ==========================================

with st.sidebar:
    st.markdown("### ⚙️ Auditor Configuration")
    audit_mode = st.selectbox(
        "Audit Rigor Profile",
        ["High-Throughput Screen", "Rigorous Peer-Review Simulation", "Clinical / Regulatory Grade", "Bioinformatic Pipeline Audit"],
        key="auditor_rigor_profile"
    )
    
    st.markdown("---")
    st.markdown("### 🎛️ Sensitivity Parameters")
    alpha_threshold = st.slider("Alpha Significance Level ($\alpha$)", 0.001, 0.100, 0.050, 0.001, key="auditor_alpha")
    power_target = st.slider("Target Statistical Power ($1 - \beta$)", 0.80, 0.99, 0.90, 0.01, key="auditor_power")
    monte_carlo_sims = st.selectbox("Monte Carlo Iterations", [1000, 5000, 10000, 50000], index=1, key="auditor_mc_sims")
    
    st.markdown("---")
    st.markdown("### 🛡️ Automated Safeguards")
    st.toggle("Real-time Confounder Flagging", value=True, key="auditor_confounder_toggle")
    st.toggle("Bayesian Prior Correction", value=True, key="auditor_bayesian_toggle")
    st.toggle("False Discovery Rate (FDR) Guard", value=True, key="auditor_fdr_toggle")

# ==========================================
# 2. MAIN APPLICATION WORKSPACE
# ==========================================

# Render core interactive UI module with stateful hooks
render_methodology_auditor_ui(
    rigor_profile=audit_mode,
    alpha=alpha_threshold,
    target_power=power_target,
    iterations=monte_carlo_sims
)